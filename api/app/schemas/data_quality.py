"""Pydantic schemas for data quality reports."""

from pydantic import BaseModel


class QualityReport(BaseModel):
    """Quality report for a dataset table."""

    table_name: str
    total_rows: int = 0
    null_counts: dict[str, int] = {}
    duplicate_rows: int = 0
    issues: list[str] = []
