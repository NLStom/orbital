"""
StatsTool - Get statistics about a table.
"""

from typing import Any


class StatsTool:
    """
    Tool for getting table statistics.

    Returns descriptive statistics and metadata about a table.
    """

    name = "stats"
    description = "Get statistics and metadata about a table"

    def __init__(self, data_loader: Any):
        self._loader = data_loader

    def execute(self, table: str) -> dict:
        """
        Get statistics for a table.

        Args:
            table: Name of the table to analyze

        Returns:
            Dict with row count, column info, and basic statistics
        """
        # Efficient row count via SQL
        count_result = self._loader.execute_sql(
            f'SELECT COUNT(*) as cnt FROM {table}'
        )
        row_count = count_result["data"][0]["cnt"] if count_result["data"] else 0

        # Full table for describe stats
        df = self._loader.get_table(table)

        result = {
            "table": table,
            "row_count": row_count,
            "columns": list(df.columns),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
        }

        # Add descriptive stats for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            stats = df[numeric_cols].describe().to_dict()
            result["numeric_stats"] = stats

        # Add value counts for categorical columns (limited)
        cat_cols = df.select_dtypes(include=["object", "category", "str"]).columns
        if len(cat_cols) > 0:
            result["categorical_summary"] = {}
            for col in cat_cols[:5]:  # Limit to first 5 categorical columns
                top_values = df[col].value_counts().head(5).to_dict()
                result["categorical_summary"][col] = {
                    "unique_count": df[col].nunique(),
                    "top_values": {str(k): v for k, v in top_values.items()},
                }

        return result
