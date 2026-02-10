"""DataLoader - Unified data access layer."""

from typing import Optional

import pandas as pd

from app.data.pg_connector import PostgreSQLConnector
from app.config import get_settings


class DataLoader:
    """
    Unified data loading interface.
    Uses PostgreSQL as the query engine.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        session_id: Optional[str] = None,
        dataset_ids: list[str] | None = None,
    ):
        self._database_url = database_url or get_settings().database_url
        self._session_id = session_id
        self._connector = PostgreSQLConnector(
            database_url=self._database_url,
            session_id=session_id,
            dataset_ids=dataset_ids,
        )

    def list_tables(self) -> list[str]:
        """List source tables."""
        return self._connector.list_tables()

    def list_derived_tables(self) -> list[str]:
        """List agent-created derived tables."""
        return self._connector.list_derived_tables()

    def get_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Get a table by name."""
        return self._connector.get_table(table_name, limit=limit)

    def execute_sql(self, sql: str) -> dict:
        """Execute SQL (SELECT, CREATE TABLE, etc.)."""
        return self._connector.execute_sql(sql)

    def get_schema(self) -> dict:
        """Get schema for all tables (source + derived)."""
        return self._connector.get_schema()

    def register_dataframe(self, name: str, df: pd.DataFrame) -> None:
        """Register a DataFrame as a queryable table."""
        self._connector.register_dataframe(name, df)

    def cleanup(self) -> None:
        """Clean up session resources."""
        self._connector.close()
