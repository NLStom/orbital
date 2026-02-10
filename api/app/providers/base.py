"""
Abstract base classes for LLM providers.

Defines the common interface that all providers must implement,
enabling multi-model support with consistent behavior.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Normalized tool call from any provider."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized response from any provider."""

    content: str | None
    tool_calls: list[ToolCall]
    stop_reason: str  # "end_turn", "tool_use", "max_tokens"
    usage: dict[str, int]  # {"input_tokens": X, "output_tokens": Y}


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider (Claude, Gemini, OpenAI) implements this interface
    to normalize their responses to a common format.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        system: str | None = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            system: Optional system prompt text

        Returns:
            Normalized LLMResponse
        """
        pass

    @abstractmethod
    def format_tools(self, tools: list[dict]) -> list[dict]:
        """Convert standard tool definitions to provider-specific format."""
        pass

    @abstractmethod
    def format_messages(self, messages: list[dict]) -> list[dict]:
        """Convert standard message format to provider-specific format."""
        pass

    @abstractmethod
    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        """Format a tool result for the provider."""
        pass
