"""
Pydantic models for request/response validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model with session-based persistence."""

    sessionId: str = Field(..., description="Session ID (UUID) for message persistence")
    message: str = Field(..., min_length=1, description="User message")
    model: str | None = Field(default=None, description="Model to use (e.g., 'gemini-flash')")


class ChartSpec(BaseModel):
    """Chart visualization specification."""

    type: str = Field(..., description="Chart type (bar, line, scatter, pie, area)")
    title: str = Field(..., description="Chart title")
    data: list[dict[str, Any]] = Field(..., description="Chart data points")
    x: str = Field(..., description="X-axis column")
    y: str = Field(..., description="Y-axis column")
    color: str | None = Field(default=None, description="Optional color grouping column")
    x_label: str | None = Field(default=None, description="Optional x-axis label")
    y_label: str | None = Field(default=None, description="Optional y-axis label")


class GraphSpec(BaseModel):
    """Graph/network visualization specification."""

    type: str = Field(default="network", description="Graph type")
    title: str = Field(..., description="Graph title")
    nodes: list[dict[str, Any]] = Field(..., description="Graph nodes")
    edges: list[dict[str, Any]] = Field(..., description="Graph edges")
    layout: str = Field(default="force", description="Layout algorithm")


class ToolCall(BaseModel):
    """Record of a tool call made by the agent."""

    tool: str = Field(..., description="Tool name")
    input: dict[str, Any] = Field(..., description="Tool input parameters")
    durationMs: int | None = Field(default=None, description="Execution time in ms")
    error: str | None = Field(default=None, description="Error message if failed")
    output: str | None = Field(default=None, description="Truncated tool output")


class QueryResult(BaseModel):
    """Query result from a query_table tool call."""

    data: list[dict[str, Any]] = Field(..., description="Row objects")
    columns: list[str] = Field(..., description="Column names")
    row_count: int = Field(..., description="Total rows returned")


class ChatResponse(BaseModel):
    """Chat response model with message persistence."""

    messageId: str = Field(..., description="UUID of saved assistant message")
    response: str = Field(..., description="Assistant response")
    visualizations: list[dict[str, Any]] = Field(
        default_factory=list, description="Combined chart and graph specifications"
    )
    model: str | None = Field(default=None, description="Model used for this response")
    toolCalls: list[ToolCall] = Field(
        default_factory=list, description="Tool calls made during processing"
    )
    queryResults: list[dict[str, Any]] = Field(
        default_factory=list, description="Query results from query_table tool calls"
    )
    tokenUsage: dict[str, int] | None = Field(
        default=None,
        description="Token usage: input_tokens (context fill) and context_limit",
    )
