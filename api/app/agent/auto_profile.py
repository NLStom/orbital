"""Auto-profiling utilities for uploaded datasets."""

import logging
from typing import Any

from app.data.loader import DataLoader

logger = logging.getLogger(__name__)


def generate_table_profile(
    data_loader: DataLoader,
    pg_table_name: str,
    display_name: str = "",
) -> dict[str, Any]:
    """Generate a statistical profile for a database table."""
    profile: dict[str, Any] = {
        "table_name": display_name or pg_table_name,
        "pg_table_name": pg_table_name,
        "columns": [],
        "row_count": 0,
    }
    try:
        schema = data_loader.get_schema(pg_table_name)
        profile["columns"] = schema if schema else []
    except Exception as e:
        logger.warning(f"Failed to profile table {pg_table_name}: {e}")
    return profile


def generate_suggested_questions(profile: dict[str, Any]) -> list[str]:
    """Generate suggested questions based on a table profile."""
    table_name = profile.get("table_name", "the data")
    return [
        f"What are the key trends in {table_name}?",
        f"Show me summary statistics for {table_name}.",
        f"Are there any outliers or anomalies in {table_name}?",
    ]
