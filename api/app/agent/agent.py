"""
OrbitalAgent - AI agent for exploratory data analysis.

Uses LLM providers with tool_use to analyze datasets, generate visualizations,
and discover patterns in relational data.
"""

import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Optional

logger = logging.getLogger(__name__)

from app.agent.context_manager import build_system_prompt
from app.agent.tool_definitions import ALL_TOOL_DEFINITIONS
from app.config import get_settings
from app.data.loader import DataLoader
from app.prompts import load_prompt
from app.tools.chart import ChartTool
from app.tools.query import RunSQLTool
from app.tools.schema import SchemaTool
from app.tools.stats import StatsTool
from app.tools.train_model import TrainModelTool
from app.tools.memory import MemoryTool
from app.tools.report import CreateReportTool

if TYPE_CHECKING:
    from app.providers.base import LLMProvider
    from app.storage.file_storage import FileStorage

class OrbitalAgent:
    """
    AI agent for exploratory data analysis.

    Uses pluggable LLM providers to analyze datasets, generate visualizations,
    and discover patterns in relational data.
    """

    def __init__(
        self,
        client: Any = None,
        provider: Optional["LLMProvider"] = None,
        data_loader: DataLoader | None = None,
        dataset_storage: Any = None,
        database_url: str | None = None,
        storage: Optional["FileStorage"] = None,
    ):
        """
        Initialize the OrbitalAgent.

        Args:
            client: Legacy Anthropic client (for backwards compatibility)
            provider: LLMProvider instance for multi-model support
            data_loader: DataLoader instance for data access
            dataset_storage: DatasetStorage instance for Phase 2 tools
            database_url: Database URL for Phase 2 tools
            storage: FileStorage for session memory persistence
        """
        self.client = client
        self.provider = provider
        self._data_loader = data_loader or DataLoader()
        self._dataset_storage = dataset_storage
        self._database_url = database_url or ""
        self._storage = storage
        self._conversations: dict[str, list[dict]] = {}
        self._current_session_id: str | None = None

        settings = get_settings()
        self.system_prompt = load_prompt(settings.system_prompt_name)

        # Initialize tools
        self._sql_tool = RunSQLTool(self._data_loader)
        self._schema_tool = SchemaTool(self._data_loader)
        self._stats_tool = StatsTool(self._data_loader)
        self._chart_tool = ChartTool(self._data_loader)
        self._train_model_tool = TrainModelTool(self._data_loader)
        self._report_tool = CreateReportTool(self._data_loader, self._storage)

        # Memory tool (needs storage for persistence)
        self._memory_tool = MemoryTool(storage) if storage else None

        # Tool definitions for Claude API
        self.tools = ALL_TOOL_DEFINITIONS

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result as JSON string."""
        try:
            if tool_name == "get_schema":
                result = self._schema_tool.execute()
            elif tool_name == "get_stats":
                result = self._stats_tool.execute(table=tool_input["table"])
            elif tool_name == "run_sql":
                result = self._sql_tool.execute(sql=tool_input["sql"])
            elif tool_name == "create_chart":
                result = self._chart_tool.execute(
                    table=tool_input["table"],
                    chart_type=tool_input["chart_type"],
                    x=tool_input["x"],
                    y=tool_input["y"],
                    title=tool_input.get("title"),
                    color=tool_input.get("color"),
                    limit=tool_input.get("limit", 100),
                    x_label=tool_input.get("x_label"),
                    y_label=tool_input.get("y_label"),
                    top_n=tool_input.get("top_n", 10),
                    group_other=tool_input.get("group_other", False),
                    series=tool_input.get("series"),
                    reference_lines=tool_input.get("reference_lines"),
                    dashed=tool_input.get("dashed"),
                )
            elif tool_name == "create_report":
                result = self._report_tool.execute(
                    session_id=self._current_session_id,
                    title=tool_input["title"],
                    sections=tool_input["sections"],
                )
            elif tool_name == "train_model":
                result = self._train_model_tool.execute(
                    table=tool_input["table"],
                    target=tool_input["target"],
                    features=tool_input.get("features"),
                    model_type=tool_input.get("model_type", "auto"),
                    algorithm=tool_input.get("algorithm", "random_forest"),
                    test_size=tool_input.get("test_size", 0.2),
                    random_state=tool_input.get("random_state", 42),
                    split_by=tool_input.get("split_by"),
                )

            # Memory tool
            elif tool_name == "update_memory":
                if self._memory_tool and self._current_session_id:
                    result = self._memory_tool.execute(
                        tool_input=tool_input,
                        session_id=self._current_session_id,
                    )
                else:
                    result = {"error": "Memory tool not available (missing storage or session_id)"}
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            result = {"error": str(e)}

        return json.dumps(result, indent=2, default=str)

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        max_turns: int = 20,
        history: list[dict] | None = None,
    ) -> dict:
        """
        Process a user message and generate a response.

        Uses tool_use loop to allow the LLM to call tools and analyze results
        before generating a final response.

        Args:
            message: User's input message
            conversation_id: Optional conversation ID for context
            max_turns: Maximum tool-use turns before stopping
            history: Pre-loaded conversation history from storage

        Returns:
            Dict with response, conversation_id, and visualizations
        """
        # Use provider-based processing if available
        if self.provider:
            return await self._process_with_provider(
                message, conversation_id, max_turns, history
            )

        raise ValueError("No LLM provider configured")

    async def _process_with_provider(
        self,
        message: str,
        conversation_id: str | None = None,
        max_turns: int = 20,
        external_history: list[dict] | None = None,
    ) -> dict:
        """Process message using the LLMProvider interface."""

        # Generate conversation ID if not provided
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        # Track session ID for memory tool
        self._current_session_id = conversation_id

        logger.info(f"[Agent] Processing message for conversation {conversation_id[:8]}...")
        logger.debug(f"[Agent] User message: {message[:200]}{'...' if len(message) > 200 else ''}")

        # Initialize conversation history from external source if provided
        # This is crucial for session persistence across server restarts
        if external_history is not None:
            self._conversations[conversation_id] = external_history
        elif conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        history = self._conversations[conversation_id]

        # Add user message to history
        history.append({"role": "user", "content": message})

        # Build system prompt with memory (dynamic per request)
        memory = None
        if self._storage and conversation_id:
            session_data = self._storage.get_session(conversation_id)
            if session_data:
                memory = session_data.get("memory")
        current_system_prompt = build_system_prompt(
            base_prompt=self.system_prompt,
            datasets=[],
            memory=memory,
        )

        # Track charts, graphs, query results, and tool calls
        charts = []
        graphs = []
        query_results = []
        tool_calls_made = []
        last_input_tokens = 0

        # Tool use loop
        for turn in range(max_turns):
            logger.info(f"[Agent] Turn {turn + 1}/{max_turns} - calling LLM...")

            # Prepare history for LLM (convert system messages)
            llm_messages = self._prepare_history_for_llm(history)

            # Call LLM via provider
            response = await self.provider.generate(
                messages=llm_messages,
                tools=self.tools,
                max_tokens=4096,
                system=current_system_prompt,
            )

            last_input_tokens = response.usage.get("input_tokens", 0)

            logger.info(
                f"[Agent] LLM response: stop_reason={response.stop_reason}, "
                f"tool_calls={len(response.tool_calls)}, "
                f"content_len={len(response.content) if response.content else 0}"
            )

            # Check if we need to execute tools
            if response.stop_reason == "tool_use" and response.tool_calls:
                # Process tool calls
                tool_results = []

                # Check for ask_user pseudo-tool — break immediately and
                # return the question so the frontend can display it.
                ask_user_call = next(
                    (tc for tc in response.tool_calls if tc.name == "ask_user"), None
                )
                if ask_user_call:
                    question = ask_user_call.arguments.get("question", "")
                    logger.info("[Agent] ask_user invoked — returning question to frontend")
                    tool_calls_made.append(
                        {
                            "tool": "ask_user",
                            "input": ask_user_call.arguments,
                            "durationMs": 0,
                        }
                    )
                    # Store assistant turn so the conversation can resume
                    history.append(
                        {
                            "role": "assistant",
                            "content": question,
                        }
                    )
                    return {
                        "response": question,
                        "conversation_id": conversation_id,
                        "charts": charts,
                        "graphs": graphs,
                        "query_results": query_results,
                        "tool_calls": tool_calls_made,
                        "is_question": True,
                        "token_usage": {"input_tokens": last_input_tokens},
                    }

                for tc in response.tool_calls:
                    tool_name = tc.name
                    tool_input = tc.arguments

                    logger.info(f"[Agent] Executing tool: {tool_name}")
                    logger.debug(f"[Agent] Tool input: {json.dumps(tool_input, default=str)[:500]}")

                    # Execute the tool with duration tracking
                    start_time = time.time()
                    result = self._execute_tool(tool_name, tool_input)
                    duration_ms = int((time.time() - start_time) * 1000)

                    logger.debug(
                        f"[Agent] Tool result: {result[:500]}{'...' if len(result) > 500 else ''}"
                    )

                    # Truncate output for logging (max 2000 chars)
                    truncated_output = result[:2000] + ("..." if len(result) > 2000 else "")

                    # Track tool calls with duration and output
                    tool_calls_made.append(
                        {
                            "tool": tool_name,
                            "input": tool_input,
                            "durationMs": duration_ms,
                            "output": truncated_output,
                        }
                    )

                    # Check if this is a visualization or query tool
                    if tool_name == "create_chart":
                        try:
                            result_data = json.loads(result)
                            if "spec" in result_data:
                                charts.append(result_data["spec"])
                        except json.JSONDecodeError:
                            pass
                    elif tool_name == "run_sql":
                        try:
                            result_data = json.loads(result)
                            if (
                                "data" in result_data
                                and "columns" in result_data
                                and result_data["data"]
                            ):
                                query_results.append(
                                    {
                                        "data": result_data["data"],
                                        "columns": result_data["columns"],
                                        "row_count": result_data.get(
                                            "row_count", len(result_data["data"])
                                        ),
                                    }
                                )
                        except (json.JSONDecodeError, KeyError):
                            pass

                    tool_results.append(self.provider.format_tool_result(tc.id, result))

                # Build assistant message content with tool_use blocks
                # This is required for Claude API - tool_result must reference tool_use in previous message
                assistant_content = []
                if response.content:
                    assistant_content.append({"type": "text", "text": response.content})
                for tc in response.tool_calls:
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )

                # Add assistant message with tool use blocks
                history.append(
                    {
                        "role": "assistant",
                        "content": assistant_content,
                    }
                )

                # Add tool results
                history.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )

            else:
                # No more tool use, extract final response
                text = response.content or ""

                logger.info(
                    f"[Agent] Final response generated: {len(text)} chars, "
                    f"{len(charts)} charts, {len(graphs)} graphs"
                )
                logger.debug(
                    f"[Agent] Response preview: {text[:300]}{'...' if len(text) > 300 else ''}"
                )

                history.append(
                    {
                        "role": "assistant",
                        "content": text,
                    }
                )

                return {
                    "response": text,
                    "conversation_id": conversation_id,
                    "charts": charts,
                    "graphs": graphs,
                    "query_results": query_results,
                    "tool_calls": tool_calls_made,
                    "token_usage": {"input_tokens": last_input_tokens},
                }

        # Max turns reached
        logger.warning(f"[Agent] Max turns ({max_turns}) reached without conclusion")
        return {
            "response": "I've made many tool calls but haven't reached a conclusion. Please try a more specific question.",
            "conversation_id": conversation_id,
            "charts": charts,
            "graphs": graphs,
            "query_results": query_results,
            "tool_calls": tool_calls_made,
            "token_usage": {"input_tokens": last_input_tokens},
        }

    def _prepare_history_for_llm(self, history: list[dict]) -> list[dict]:
        """
        Transform conversation history for LLM consumption.

        System messages (role="system") are converted to user messages with
        a [Context] prefix. Consecutive system messages are batched into a
        single user message to save tokens.
        """
        result: list[dict] = []
        i = 0
        while i < len(history):
            msg = history[i]
            if msg.get("role") == "system":
                # Collect consecutive system messages
                system_contents = []
                while i < len(history) and history[i].get("role") == "system":
                    content = history[i]["content"]
                    system_event = history[i].get("systemEvent")
                    if system_event and system_event.get("metadata"):
                        content = f"{content}\nDetails: {json.dumps(system_event['metadata'])}"
                    system_contents.append(content)
                    i += 1
                # Batch into one user message
                batched = "\n".join(f"- {c}" for c in system_contents)
                result.append({
                    "role": "user",
                    "content": f"[Context]\n{batched}",
                })
            else:
                result.append(msg)
                i += 1
        return result

    def reset_conversation(self, conversation_id: str) -> None:
        """Clear a specific conversation's history."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]

    def reset_all(self) -> None:
        """Clear all conversation histories."""
        self._conversations = {}
