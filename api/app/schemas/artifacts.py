"""Pydantic schemas for Artifact-related models."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from .sessions import DataSource


class DataSnapshot(BaseModel):
    """Frozen data captured when artifact was created."""

    query: str | None = None
    data: list[Any] = []
    columns: list[str] = []
    rowCount: int = 0
    capturedAt: str


class ArtifactCreate(BaseModel):
    """Request to create an artifact."""

    sessionId: str = Field(..., min_length=1)
    insightId: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)


class Artifact(BaseModel):
    """A full artifact with all data."""

    id: str
    name: str
    description: str = ""
    createdAt: str
    sessionId: str
    insightId: str | None = None
    dataSource: DataSource
    visualization: dict[str, Any]
    dataSnapshot: DataSnapshot


class ArtifactSummary(BaseModel):
    """Summary of an artifact for list views."""

    id: str
    name: str
    description: str = ""
    createdAt: str
    dataSource: DataSource
    visualizationType: Literal["chart", "graph", "report"]


class ArtifactListResponse(BaseModel):
    """Response for listing artifacts."""

    artifacts: list[ArtifactSummary]
