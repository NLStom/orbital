"""
SchemaTool - Get schema information about available data.
"""

from typing import Any


class SchemaTool:
    """
    Tool for getting schema information.

    Returns information about available tables and their structure.
    """

    name = "schema"
    description = "Get schema information about available tables"

    def __init__(self, data_loader: Any):
        """
        Initialize the SchemaTool.

        Args:
            data_loader: DataLoader instance for data access
        """
        self._loader = data_loader

    def execute(self) -> dict:
        """
        Get schema for all tables.

        Returns:
            Dict with tables and their schema information
        """
        return self._loader.get_schema()
