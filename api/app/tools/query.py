"""RunSQLTool - Execute SQL queries and create derived tables."""

from typing import Any


class RunSQLTool:
    """
    Execute SQL against the data source.

    Supports:
    - SELECT queries (return data)
    - CREATE TABLE AS SELECT (create derived tables)
    - JOINs across source and derived tables
    """

    name = "run_sql"

    def __init__(self, data_loader: Any):
        self._loader = data_loader

    def execute(self, sql: str) -> dict:
        """
        Execute a SQL query.

        Args:
            sql: SQL statement (SELECT, CREATE TABLE AS SELECT, etc.)

        Returns:
            Dict with data/columns/row_count for SELECT,
            or created_table/message for CREATE.
        """
        try:
            return self._loader.execute_sql(sql)
        except Exception as e:
            return {"error": f"SQL failed: {e}", "data": [], "columns": []}
