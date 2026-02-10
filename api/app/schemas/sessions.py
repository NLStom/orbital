"""Pydantic schemas for Session-related models."""

from typing import Any, Literal

from pydantic import BaseModel, Field

DataSource = Literal["custom"]


class MemoryEntry(BaseModel):
    """A single memory entry with timestamp."""

    content: str
    added_at: str


class Memory(BaseModel):
    """Session-scoped agent memory."""

    facts: list[MemoryEntry] = []
    preferences: list[MemoryEntry] = []
    corrections: list[MemoryEntry] = []
    conclusions: list[MemoryEntry] = []


class MessageCreate(BaseModel):
    """Request to create a message."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)
    charts: list[dict[str, Any]] | None = None
    graphs: list[dict[str, Any]] | None = None
    systemEvent: dict[str, Any] | None = None


class Message(BaseModel):
    """A chat message in a session."""

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str
    charts: list[dict[str, Any]] | None = None
    graphs: list[dict[str, Any]] | None = None
    toolCalls: list[dict[str, Any]] | None = None
    queryResults: list[dict[str, Any]] | None = None
    systemEvent: dict[str, Any] | None = None


class InsightCreate(BaseModel):
    """Request to create an insight."""

    title: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(..., min_length=1, max_length=500)
    messageId: str | None = None
    visualization: dict[str, Any] | None = None


class InsightUpdate(BaseModel):
    """Request to update an insight."""

    id: str
    savedAsArtifact: str | None = None


class Insight(BaseModel):
    """An extracted insight from a session."""

    id: str
    title: str
    summary: str
    createdAt: str
    messageId: str | None = None
    visualization: dict[str, Any] | None = None
    savedAsArtifact: str | None = None


class SessionCreate(BaseModel):
    """Request to create a session."""

    dataSource: DataSource
    name: str | None = Field(default=None, max_length=100)
    dataset_ids: list[str] | None = Field(default=None, description="Datasets to attach at creation")


class SessionUpdate(BaseModel):
    """Request to update a session."""

    name: str | None = Field(default=None, max_length=100)
    addMessage: MessageCreate | None = None
    addInsight: InsightCreate | None = None
    updateInsight: InsightUpdate | None = None
    # Context management: update summary cache
    historySummary: str | None = None
    historySummaryUpToIndex: int | None = None


class Session(BaseModel):
    """A full session with all data."""

    id: str
    name: str
    dataSource: DataSource
    createdBy: str = "unknown"
    createdAt: str
    updatedAt: str
    messages: list[Message] = []
    insights: list[Insight] = []
    datasets: list[str] = []
    memory: Memory = Field(default_factory=Memory)
    # Context management: cached summary for long conversations
    historySummary: str | None = None
    historySummaryUpToIndex: int | None = None


class SessionSummary(BaseModel):
    """Summary of a session for list views."""

    id: str
    name: str
    dataSource: DataSource
    createdBy: str = "unknown"
    createdAt: str
    updatedAt: str
    messageCount: int
    userMessageCount: int
    artifactCount: int
    datasetCount: int


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionSummary]
