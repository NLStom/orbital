"""
FileStorage - JSON file-based storage for sessions and artifacts.

Uses atomic writes (write to temp file, then rename) to prevent corruption.
"""

import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path


class FileStorage:
    """
    File-based storage for sessions and artifacts.

    Directory structure:
        data_dir/
        ├── sessions/
        │   └── {uuid}.json
        └── artifacts/
            └── {uuid}.json
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize storage with data directory.

        Args:
            data_dir: Root directory for data. Defaults to orbital/data.
        """
        if data_dir is None:
            # Default to orbital/data relative to this file
            data_dir = Path(__file__).parent.parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.artifacts_dir = self.data_dir / "artifacts"

        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_user(self) -> str:
        """Get current user from env var or system username."""
        return os.getenv("ORBITAL_USER") or os.getenv("USER") or "unknown"

    def _now_iso(self) -> str:
        """Return current UTC timestamp in ISO 8601 format."""
        return datetime.now(UTC).isoformat()

    def _generate_id(self) -> str:
        """Generate a UUID v4 string."""
        return str(uuid.uuid4())

    def _write_json(self, path: Path, data: dict) -> None:
        """
        Write data to JSON file atomically.

        Writes to a temp file first, then renames to prevent corruption.
        """
        # Write to temp file in same directory (for atomic rename)
        fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="tmp_", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            # Atomic rename
            os.replace(temp_path, path)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _read_json(self, path: Path) -> dict | None:
        """Read JSON file, returns None if not found."""
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    # ========== Sessions ==========

    def list_sessions(self) -> list[dict]:
        """
        List all sessions as SessionSummary objects.

        Returns list sorted by updatedAt descending (most recent first).
        """
        summaries = []

        for file_path in self.sessions_dir.glob("*.json"):
            data = self._read_json(file_path)
            if data:
                # Count artifacts (insights with savedAsArtifact set)
                artifact_count = sum(
                    1 for insight in data.get("insights", []) if insight.get("savedAsArtifact")
                )

                summaries.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "dataSource": data["dataSource"],
                        "createdBy": data.get("createdBy", "unknown"),
                        "createdAt": data["createdAt"],
                        "updatedAt": data["updatedAt"],
                        "messageCount": len(data.get("messages", [])),
                        "userMessageCount": len(
                            [m for m in data.get("messages", []) if m.get("role") == "user"]
                        ),
                        "artifactCount": artifact_count,
                        "datasetCount": len(data.get("datasets", [])),
                    }
                )

        # Sort by updatedAt descending
        summaries.sort(key=lambda x: x["updatedAt"], reverse=True)
        return summaries

    def get_session(self, session_id: str) -> dict | None:
        """
        Get a session by ID.

        Returns full Session object or None if not found.
        Ensures backward compatibility by adding empty memory if missing.
        """
        path = self.sessions_dir / f"{session_id}.json"
        data = self._read_json(path)
        if data is not None and "memory" not in data:
            data["memory"] = {
                "facts": [],
                "preferences": [],
                "corrections": [],
                "conclusions": [],
            }
        return data

    def create_session(self, data_source: str, name: str) -> dict:
        """
        Create a new session.

        Args:
            data_source: One of vndb, polymarket, steam, custom
            name: Session name (trimmed, defaults to "Untitled Session" if empty)

        Returns:
            Created Session object
        """
        # Trim and default name
        name = name.strip() if name else ""
        if not name:
            name = "Untitled Session"

        now = self._now_iso()
        session = {
            "id": self._generate_id(),
            "name": name,
            "dataSource": data_source,
            "createdBy": self._get_current_user(),
            "createdAt": now,
            "updatedAt": now,
            "messages": [],
            "insights": [],
            "datasets": [],
            "memory": {
                "facts": [],
                "preferences": [],
                "corrections": [],
                "conclusions": [],
            },
        }

        path = self.sessions_dir / f"{session['id']}.json"
        self._write_json(path, session)

        return session

    def update_session(self, session_id: str, updates: dict) -> dict | None:
        """
        Update a session.

        Supported operations:
        - name: Replace session name
        - addMessage: Append message to messages array
        - addInsight: Append insight to insights array
        - updateInsight: Update existing insight by id

        Returns updated Session or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        # Handle simple field updates
        if "name" in updates:
            session["name"] = updates["name"]

        # Handle history summary cache updates
        if "historySummary" in updates:
            session["historySummary"] = updates["historySummary"]
        if "historySummaryUpToIndex" in updates:
            session["historySummaryUpToIndex"] = updates["historySummaryUpToIndex"]

        # Handle memory update (full replacement of memory dict)
        if "memory" in updates:
            session["memory"] = updates["memory"]

        # Handle addDataset
        if "addDataset" in updates:
            dataset_id = updates["addDataset"]
            if "datasets" not in session:
                session["datasets"] = []
            if dataset_id not in session["datasets"]:
                session["datasets"].append(dataset_id)

        # Handle removeDataset
        if "removeDataset" in updates:
            dataset_id = updates["removeDataset"]
            if "datasets" in session:
                session["datasets"] = [d for d in session["datasets"] if d != dataset_id]

        # Handle addMessage
        if "addMessage" in updates:
            msg_data = updates["addMessage"]
            message = {
                "id": self._generate_id(),
                "role": msg_data["role"],
                "content": msg_data["content"],
                "timestamp": self._now_iso(),
            }
            # Optional fields for assistant messages
            if "charts" in msg_data:
                message["charts"] = msg_data["charts"]
            if "graphs" in msg_data:
                message["graphs"] = msg_data["graphs"]
            if "toolCalls" in msg_data:
                message["toolCalls"] = msg_data["toolCalls"]
            if "systemEvent" in msg_data:
                message["systemEvent"] = msg_data["systemEvent"]

            session["messages"].append(message)

        # Handle addInsight
        if "addInsight" in updates:
            insight_data = updates["addInsight"]
            insight = {
                "id": self._generate_id(),
                "title": insight_data["title"],
                "summary": insight_data["summary"],
                "createdAt": self._now_iso(),
                "messageId": insight_data.get("messageId"),
            }
            if "visualization" in insight_data:
                insight["visualization"] = insight_data["visualization"]

            session["insights"].append(insight)

        # Handle updateInsight
        if "updateInsight" in updates:
            insight_update = updates["updateInsight"]
            insight_id = insight_update["id"]

            for insight in session["insights"]:
                if insight["id"] == insight_id:
                    # Merge updates into insight
                    for key, value in insight_update.items():
                        if key != "id":
                            if value is None:
                                # Remove the key if value is None
                                insight.pop(key, None)
                            else:
                                insight[key] = value
                    break

        # Update timestamp
        session["updatedAt"] = self._now_iso()

        # Write back
        path = self.sessions_dir / f"{session_id}.json"
        self._write_json(path, session)

        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Returns True if deleted, False if not found.
        Does NOT delete associated artifacts (they have frozen data).
        """
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return False

        path.unlink()
        return True

    def delete_empty_sessions(self) -> int:
        """
        Delete all sessions with zero user messages.

        Returns the number of sessions deleted.
        """
        deleted_count = 0

        for file_path in self.sessions_dir.glob("*.json"):
            data = self._read_json(file_path)
            if data:
                user_message_count = len(
                    [m for m in data.get("messages", []) if m.get("role") == "user"]
                )

                if user_message_count == 0:
                    file_path.unlink()
                    deleted_count += 1

        return deleted_count

    # ========== Artifacts ==========

    def list_artifacts(self) -> list[dict]:
        """
        List all artifacts as ArtifactSummary objects.

        Returns list sorted by createdAt descending (most recent first).
        """
        summaries = []

        for file_path in self.artifacts_dir.glob("*.json"):
            data = self._read_json(file_path)
            if data:
                # Determine visualization type
                viz = data.get("visualization", {})
                if viz.get("type") == "report":
                    viz_type = "report"
                elif "nodes" in viz or "edges" in viz:
                    viz_type = "graph"
                else:
                    viz_type = "chart"

                summaries.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "description": data.get("description", ""),
                        "createdAt": data["createdAt"],
                        "dataSource": data["dataSource"],
                        "visualizationType": viz_type,
                    }
                )

        # Sort by createdAt descending
        summaries.sort(key=lambda x: x["createdAt"], reverse=True)
        return summaries

    def get_artifact(self, artifact_id: str) -> dict | None:
        """
        Get an artifact by ID.

        Returns full Artifact object or None if not found.
        """
        path = self.artifacts_dir / f"{artifact_id}.json"
        return self._read_json(path)

    def create_artifact(
        self, session_id: str, insight_id: str, name: str, description: str
    ) -> dict | None:
        """
        Create an artifact from a session insight.

        Returns None if:
        - Session not found
        - Insight not found in session

        The insight's savedAsArtifact field is updated automatically.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        # Find insight
        insight = None
        for i in session["insights"]:
            if i["id"] == insight_id:
                insight = i
                break

        if insight is None:
            return None

        # Extract visualization and create data snapshot
        visualization = insight.get("visualization", {})
        data_snapshot = self._create_data_snapshot(visualization)

        now = self._now_iso()
        artifact = {
            "id": self._generate_id(),
            "name": name,
            "description": description,
            "createdAt": now,
            "sessionId": session_id,
            "insightId": insight_id,
            "dataSource": session["dataSource"],
            "visualization": visualization,
            "dataSnapshot": data_snapshot,
        }

        # Write artifact
        path = self.artifacts_dir / f"{artifact['id']}.json"
        self._write_json(path, artifact)

        # Update insight's savedAsArtifact
        self.update_session(
            session_id, {"updateInsight": {"id": insight_id, "savedAsArtifact": artifact["id"]}}
        )

        return artifact

    def create_report_artifact(
        self,
        session_id: str,
        title: str,
        description: str,
        visualization: dict,
        data_snapshot: dict,
    ) -> dict | None:
        """
        Create a report artifact directly (not from an insight).

        Returns None if session not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        now = self._now_iso()
        artifact = {
            "id": self._generate_id(),
            "name": title,
            "description": description,
            "createdAt": now,
            "sessionId": session_id,
            "insightId": None,
            "dataSource": session["dataSource"],
            "visualization": visualization,
            "dataSnapshot": data_snapshot,
        }

        path = self.artifacts_dir / f"{artifact['id']}.json"
        self._write_json(path, artifact)

        return artifact

    def _create_data_snapshot(self, visualization: dict) -> dict:
        """
        Extract data snapshot from visualization spec.

        For charts: extracts data array
        For graphs: extracts nodes and edges
        """
        data = visualization.get("data", [])

        # Extract columns from data
        columns = []
        if data and isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                columns = list(data[0].keys())

        return {
            "data": data,
            "columns": columns,
            "rowCount": len(data) if isinstance(data, list) else 0,
            "capturedAt": self._now_iso(),
        }

    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact.

        Returns True if deleted, False if not found.
        Attempts to clear savedAsArtifact from source insight.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return False

        # Try to clear reference from insight (fails silently if session gone)
        session_id = artifact.get("sessionId")
        insight_id = artifact.get("insightId")
        if session_id and insight_id:
            session = self.get_session(session_id)
            if session:
                self.update_session(
                    session_id, {"updateInsight": {"id": insight_id, "savedAsArtifact": None}}
                )

        # Delete artifact file
        path = self.artifacts_dir / f"{artifact_id}.json"
        path.unlink()
        return True
