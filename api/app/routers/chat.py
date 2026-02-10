"""
Chat router - handles chat endpoints with session persistence.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status

try:  # Anthropic errors (default provider)
    from anthropic import AnthropicError
except Exception:  # pragma: no cover - Anthropic optional in some envs
    AnthropicError = None  # type: ignore[assignment]

try:  # OpenAI client errors
    from openai import OpenAIError
except Exception:  # pragma: no cover - OpenAI optional in some envs
    OpenAIError = None  # type: ignore[assignment]

try:  # Google Vertex AI errors
    from google.api_core.exceptions import GoogleAPIError
except Exception:  # pragma: no cover - google optional in some envs
    GoogleAPIError = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

from app.dependencies import get_agent_for_source, get_storage
from app.models import ChatRequest, ChatResponse
from app.providers.factory import AVAILABLE_MODELS
from app.storage.file_storage import FileStorage

router = APIRouter(prefix="/api", tags=["chat"])

# UUID regex pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Aggregate provider-specific exception types so we can surface helpful errors
_PROVIDER_ERROR_TYPES: tuple[type[Exception], ...] = tuple(
    err for err in (AnthropicError, OpenAIError, GoogleAPIError) if err is not None
)


def _format_provider_error(exc: Exception) -> str:
    """Return a concise error message from an upstream LLM provider exception."""
    message = str(exc).strip()
    return message or exc.__class__.__name__


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, storage: FileStorage = Depends(get_storage)
):
    """
    Process a chat message with session-based persistence.

    1. Validates sessionId exists and is a valid UUID
    2. Validates message content
    3. Saves user message BEFORE calling agent
    4. Calls agent with message
    5. Saves assistant message AFTER agent responds
    6. Returns response with messageId
    """
    # 1. Validate sessionId format
    if not request.sessionId:
        raise HTTPException(status_code=400, detail="sessionId is required")

    if not UUID_PATTERN.match(request.sessionId):
        raise HTTPException(status_code=400, detail="sessionId must be a valid UUID")

    # 2. Validate session exists
    session = storage.get_session(request.sessionId)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 3. Validate message
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if len(message) > 50000:
        raise HTTPException(status_code=400, detail="message must be 50000 characters or less")

    # 4. Save user message BEFORE calling agent
    storage.update_session(request.sessionId, {"addMessage": {"role": "user", "content": message}})

    # 5. Load history from session for agent context (CM1 fix)
    # Convert persisted messages to format agent can use
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in session.get("messages", [])
    ]

    # 6. Call agent (uses sessionId as conversation_id)
    try:
        dataset_ids = session.get("datasets", []) or None
        agent, model_used = get_agent_for_source(
            session["dataSource"], model=request.model, dataset_ids=dataset_ids,
            session_id=request.sessionId,
        )
        result = await agent.process_message(
            message=message,
            conversation_id=request.sessionId,
            history=history,  # Pass persisted history to agent
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except _PROVIDER_ERROR_TYPES as e:  # type: ignore[misc]
        error_message = _format_provider_error(e)
        logger.error(
            "LLM provider error for session %s: %s", request.sessionId, error_message
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {error_message}",
        ) from e
    except Exception as e:
        logger.exception(f"Error processing message for session {request.sessionId}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message") from e

    # 7. Save assistant message AFTER agent responds
    updated_session = storage.update_session(
        request.sessionId,
        {
            "addMessage": {
                "role": "assistant",
                "content": result["response"],
                "charts": result.get("charts", []),
                "graphs": result.get("graphs", []),
                "toolCalls": result.get("tool_calls", []),
                "queryResults": result.get("query_results", []),
            }
        },
    )

    # 8. Get the messageId (last message in session)
    assistant_message = updated_session["messages"][-1]

    # 9. Build token usage with context limit from model config
    token_usage = None
    agent_token_usage = result.get("token_usage")
    if agent_token_usage:
        model_config = AVAILABLE_MODELS.get(model_used or "")
        context_limit = model_config.context_window if model_config else 200_000
        token_usage = {
            "inputTokens": agent_token_usage.get("input_tokens", 0),
            "contextLimit": context_limit,
        }

    # 10. Return response with messageId and combined visualizations
    return ChatResponse(
        messageId=assistant_message["id"],
        response=result["response"],
        visualizations=result.get("charts", []) + result.get("graphs", []),
        model=model_used,
        toolCalls=result.get("tool_calls", []),
        queryResults=result.get("query_results", []),
        tokenUsage=token_usage,
    )
