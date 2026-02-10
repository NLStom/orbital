"""
Schema Storage - File-based storage for generated ER diagram schemas.
"""

import json
import os
import time
from pathlib import Path


class SchemaStorage:
    """File-based storage for ER diagram schemas."""

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize storage.

        Args:
            data_dir: Root data directory. Schemas stored in {data_dir}/schemas/
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.schemas_dir = self.data_dir / "schemas"
        self.schemas_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, source_id: str) -> Path:
        """Get file path for a schema."""
        return self.schemas_dir / f"{source_id}.json"

    def save(self, source_id: str, schema: dict) -> None:
        """
        Save schema to file.

        Args:
            source_id: Data source identifier
            schema: ERDiagramSpec dict to save
        """
        path = self._get_path(source_id)
        with open(path, "w") as f:
            json.dump(schema, f, indent=2)

    def load(self, source_id: str) -> dict | None:
        """
        Load schema from file.

        Args:
            source_id: Data source identifier

        Returns:
            ERDiagramSpec dict or None if not found
        """
        path = self._get_path(source_id)
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)

    def exists(self, source_id: str) -> bool:
        """Check if schema file exists."""
        return self._get_path(source_id).exists()

    def is_stale(self, source_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if schema is stale (older than max_age_hours).

        Args:
            source_id: Data source identifier
            max_age_hours: Maximum age in hours before considered stale

        Returns:
            True if stale or missing, False if fresh
        """
        path = self._get_path(source_id)
        if not path.exists():
            return True

        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        age_hours = age_seconds / 3600

        return age_hours > max_age_hours

    def _get_layout_path(self, source_id: str) -> Path:
        """Get file path for a layout."""
        return self.schemas_dir / f"{source_id}-layout.json"

    def save_layout(self, source_id: str, layout: dict) -> None:
        """Save layout to file. Adds updatedAt timestamp."""
        from datetime import UTC, datetime

        layout["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        path = self._get_layout_path(source_id)
        with open(path, "w") as f:
            json.dump(layout, f, indent=2)

    def load_layout(self, source_id: str) -> dict | None:
        """Load layout from file. Returns None if not found."""
        path = self._get_layout_path(source_id)
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def delete_layout(self, source_id: str) -> bool:
        """Delete layout file. Returns True if deleted, False if not found."""
        path = self._get_layout_path(source_id)
        if not path.exists():
            return False
        path.unlink()
        return True
