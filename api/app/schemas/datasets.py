"""Pydantic schemas for Dataset models."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.data_quality import QualityReport


class DatasetTableInfo(BaseModel):
    """Information about a single table within a dataset."""

    name: str
    pg_table_name: str
    row_count: int = 0
    columns: list[str] = []
    dtypes: dict[str, str] = {}


class DatasetCreate(BaseModel):
    """Request to create a dataset (via upload)."""

    name: str = Field(..., min_length=1, max_length=200)
    owner: str = "anonymous"
    visibility: Literal["public", "private"] = "private"
    derived_from: str | None = None


class DatasetUpdate(BaseModel):
    """Request to update a dataset."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    visibility: Literal["public", "private"] | None = None


class Dataset(BaseModel):
    """Full dataset record."""

    id: str
    name: str
    owner: str
    visibility: Literal["public", "private"]
    derived_from: str | None
    tables: list[DatasetTableInfo]
    created_at: str
    updated_at: str
    quality_reports: list[QualityReport] | None = None
    suggested_questions: list[str] | None = None


class DatasetSummary(BaseModel):
    """Summary for list views."""

    id: str
    name: str
    owner: str
    visibility: Literal["public", "private"]
    derived_from: str | None
    table_count: int
    total_rows: int
    created_at: str


class DatasetListResponse(BaseModel):
    """Response for listing datasets."""

    datasets: list[DatasetSummary]
