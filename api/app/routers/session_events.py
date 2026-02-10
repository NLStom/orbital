"""
Session Events router - system events for session context.

Creates system messages that provide context to the agent
without being part of the user conversation.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import get_storage
from app.storage.pg_session_storage import PgSessionStorage

router = APIRouter(prefix="/api/sessions", tags=["session-events"])


class SystemEventCreate(BaseModel):
    """Request to create a system event."""

    type: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None


@router.post("/{session_id}/events", status_code=status.HTTP_201_CREATED)
def create_session_event(
    session_id: str,
    event: SystemEventCreate,
    storage: PgSessionStorage = Depends(get_storage),
):
    """
    Log a system event as a message in the session.

    Creates a message with role="system" and stores event data
    in the systemEvent field. The agent will see these as context.
    """
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    system_event = {
        "type": event.type,
        "summary": event.summary,
        "metadata": event.metadata,
    }

    updated = storage.update_session(
        session_id,
        {
            "addMessage": {
                "role": "system",
                "content": event.summary,
                "systemEvent": system_event,
            }
        },
    )

    # Return the created message (last one)
    return updated["messages"][-1]
