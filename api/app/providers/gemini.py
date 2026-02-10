"""
Gemini (Google) LLM provider.

Implements the LLMProvider interface for Gemini models.
"""

import logging
from typing import Any

from google import genai
from google.genai import types

from app.providers.base import LLMProvider, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini provider using Google's GenAI API."""

    # Type priority for union types (prefer more specific types)
    TYPE_PRIORITY = ["integer", "number", "boolean", "string"]

    def __init__(self, api_key: str, model_id: str):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key
            model_id: Model identifier (e.g., 'gemini-2.5-flash')
        """
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        system: str | None = None,
    ) -> LLMResponse:
        """
        Generate a response using Gemini.

        Args:
            messages: List of message dicts
            tools: Optional tool definitions
            max_tokens: Maximum tokens to generate
            system: Optional system prompt text

        Returns:
            Normalized LLMResponse
        """
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
        )

        if system:
            config.system_instruction = system

        if tools:
            config.tools = self._build_tools(tools)

        # Convert messages to Gemini format
        contents = self._build_contents(messages)

        logger.debug(f"[Gemini] Calling model {self.model_id} with {len(contents)} contents")

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config,
            )
            logger.debug(f"[Gemini] Response received: {len(response.candidates)} candidates")
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"[Gemini] API error: {type(e).__name__}: {e}")
            raise

    def format_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Convert JSON Schema tools to Gemini function declarations."""
        return self._build_tools(tools)

    def format_messages(self, messages: list[dict]) -> list[dict]:
        """Convert 'assistant' role to 'model' for Gemini."""
        formatted = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            formatted.append(
                {
                    "role": role,
                    "content": msg["content"],
                }
            )
        return formatted

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        """Format a tool result for Gemini."""
        return {
            "role": "user",
            "parts": [
                types.Part.from_function_response(
                    name=tool_call_id,
                    response={"result": result},
                )
            ],
        }

    def _transform_schema_for_gemini(self, schema: dict | None) -> dict | None:
        """
        Transform JSON Schema to be compatible with Gemini's FunctionDeclaration.

        Gemini requires 'type' to be a single enum value, not a list.
        This recursively converts union types like ["string", "number", "null"]
        to a single type (picking the most appropriate one).
        """
        if schema is None:
            return None

        schema = schema.copy()

        # Handle union types in 'type' field
        if "type" in schema:
            type_val = schema["type"]
            if isinstance(type_val, list):
                # Filter out 'null' and pick best type by priority
                non_null_types = [t for t in type_val if t != "null"]
                if non_null_types:
                    # Pick the highest priority type
                    for preferred in self.TYPE_PRIORITY:
                        if preferred in non_null_types:
                            schema["type"] = preferred
                            break
                    else:
                        # Fallback to first non-null type
                        schema["type"] = non_null_types[0]
                else:
                    # All types were null
                    schema["type"] = "string"

        # Recursively transform nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            schema["properties"] = {
                key: self._transform_schema_for_gemini(val)
                for key, val in schema["properties"].items()
            }

        # Handle array items
        if "items" in schema and isinstance(schema["items"], dict):
            schema["items"] = self._transform_schema_for_gemini(schema["items"])

        # Handle anyOf/oneOf (convert to single type)
        for keyword in ("anyOf", "oneOf"):
            if keyword in schema:
                # Take the first option's type
                options = schema.pop(keyword)
                if options and isinstance(options, list) and len(options) > 0:
                    first_option = options[0]
                    if isinstance(first_option, dict) and "type" in first_option:
                        schema["type"] = first_option["type"]

        return schema

    def _build_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Build Gemini Tool objects from standard tool definitions."""
        declarations = []
        for tool in tools:
            # Transform schema to be Gemini-compatible
            input_schema = tool.get("input_schema")
            transformed_schema = self._transform_schema_for_gemini(input_schema)

            declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=transformed_schema,
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _build_contents(self, messages: list[dict]) -> list[types.Content]:
        """Build Gemini Content objects from messages."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            content = msg["content"]

            # Handle string content
            if isinstance(content, str):
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content)])
                )
            # Handle list content (e.g., tool results, tool use blocks)
            elif isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type == "tool_result":
                            parts.append(
                                types.Part.from_function_response(
                                    name=item.get("tool_use_id", ""),
                                    response={"result": item.get("content", "")},
                                )
                            )
                        elif item_type == "tool_use":
                            # Convert Claude tool_use format to Gemini function_call
                            parts.append(
                                types.Part.from_function_call(
                                    name=item.get("name", ""),
                                    args=item.get("input", {}),
                                )
                            )
                        elif item_type == "text":
                            parts.append(types.Part.from_text(text=item.get("text", "")))
                        else:
                            parts.append(types.Part.from_text(text=str(item)))
                    else:
                        parts.append(types.Part.from_text(text=str(item)))
                if parts:
                    contents.append(types.Content(role=role, parts=parts))

        return contents

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Gemini API response to normalized format."""
        content = None
        tool_calls = []

        for candidate in response.candidates:
            # Skip candidates with no content or empty parts
            if candidate.content is None or candidate.content.parts is None:
                continue
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    content = part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append(
                        ToolCall(
                            id=fc.name,  # Gemini uses name as ID
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {},
                        )
                    )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
            },
        )
