"""PostgreSQL-backed storage for sessions and artifacts."""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Optional

import psycopg


class PgSessionStorage:
    """
    PostgreSQL storage for sessions and artifacts.

    Replaces FileStorage with database-backed persistence.
    Follows the same interface so routers/agent need no logic changes.
    """

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._conn: Optional[psycopg.Connection] = None

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._database_url, autocommit=False)
        return self._conn

    def initialize(self) -> None:
        """Create sessions and artifacts tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT 'Untitled Session',
                    data_source TEXT NOT NULL DEFAULT 'custom',
                    created_by TEXT NOT NULL DEFAULT 'anonymous',
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    insight_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    data_source TEXT NOT NULL DEFAULT 'custom',
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _get_current_user() -> str:
        return os.getenv("ORBITAL_USER") or os.getenv("USER") or "unknown"

    def _ts(self, val) -> str:
        """Convert a datetime or string to ISO string."""
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    # ── sessions ─────────────────────────────────────────────

    def create_session(self, data_source: str, name: str) -> dict:
        name = name.strip() if name else ""
        if not name:
            name = "Untitled Session"

        now = self._now_iso()
        session_id = self._generate_id()
        data = {
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

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (id, name, data_source, created_by, data, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, data_source, created_by, data, created_at, updated_at
                """,
                (session_id, name, data_source, self._get_current_user(), json.dumps(data), now, now),
            )
            row = cur.fetchone()
        self.conn.commit()
        return self._session_row_to_dict(row)

    def get_session(self, session_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, data_source, created_by, data, created_at, updated_at FROM sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
        self.conn.rollback()
        if row is None:
            return None
        return self._session_row_to_dict(row)

    def list_sessions(self) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, data_source, created_by, data, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
        self.conn.rollback()

        summaries = []
        for row in rows:
            d = self._session_row_to_dict(row)
            messages = d.get("messages", [])
            insights = d.get("insights", [])
            artifact_count = sum(1 for ins in insights if ins.get("savedAsArtifact"))
            summaries.append({
                "id": d["id"],
                "name": d["name"],
                "dataSource": d["dataSource"],
                "createdBy": d["createdBy"],
                "createdAt": d["createdAt"],
                "updatedAt": d["updatedAt"],
                "messageCount": len(messages),
                "userMessageCount": len([m for m in messages if m.get("role") == "user"]),
                "artifactCount": artifact_count,
                "datasetCount": len(d.get("datasets", [])),
            })
        return summaries

    def update_session(self, session_id: str, updates: dict) -> dict | None:
        # Fetch current row
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, data_source, created_by, data, created_at, updated_at FROM sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()

        if row is None:
            self.conn.rollback()
            return None

        session = self._session_row_to_dict(row)
        data = row[4]
        if isinstance(data, str):
            data = json.loads(data)

        # Rebuild full mutable state from merged dict
        name = session["name"]

        if "name" in updates:
            name = updates["name"]

        if "historySummary" in updates:
            data["historySummary"] = updates["historySummary"]
        if "historySummaryUpToIndex" in updates:
            data["historySummaryUpToIndex"] = updates["historySummaryUpToIndex"]

        if "memory" in updates:
            data["memory"] = updates["memory"]

        if "addDataset" in updates:
            datasets = data.get("datasets", [])
            ds_id = updates["addDataset"]
            if ds_id not in datasets:
                datasets.append(ds_id)
            data["datasets"] = datasets

        if "removeDataset" in updates:
            ds_id = updates["removeDataset"]
            data["datasets"] = [d for d in data.get("datasets", []) if d != ds_id]

        if "addMessage" in updates:
            msg_data = updates["addMessage"]
            message = {
                "id": self._generate_id(),
                "role": msg_data["role"],
                "content": msg_data["content"],
                "timestamp": self._now_iso(),
            }
            for key in ("charts", "graphs", "toolCalls", "systemEvent", "queryResults"):
                if key in msg_data:
                    message[key] = msg_data[key]
            data.setdefault("messages", []).append(message)

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
            data.setdefault("insights", []).append(insight)

        if "updateInsight" in updates:
            insight_update = updates["updateInsight"]
            insight_id = insight_update["id"]
            for insight in data.get("insights", []):
                if insight["id"] == insight_id:
                    for key, value in insight_update.items():
                        if key != "id":
                            if value is None:
                                insight.pop(key, None)
                            else:
                                insight[key] = value
                    break

        now = self._now_iso()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sessions SET name = %s, data = %s, updated_at = %s
                WHERE id = %s
                RETURNING id, name, data_source, created_by, data, created_at, updated_at
                """,
                (name, json.dumps(data), now, session_id),
            )
            row = cur.fetchone()
        self.conn.commit()
        if row is None:
            return None
        return self._session_row_to_dict(row)

    def delete_session(self, session_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def delete_empty_sessions(self) -> int:
        """Delete sessions with zero user messages."""
        # We need to find sessions where JSONB data->'messages' has no user messages.
        # Use a subquery to filter.
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM sessions
                WHERE id IN (
                    SELECT id FROM sessions
                    WHERE NOT EXISTS (
                        SELECT 1 FROM jsonb_array_elements(data->'messages') AS m
                        WHERE m->>'role' = 'user'
                    )
                )
            """)
            deleted = cur.rowcount
        self.conn.commit()
        return deleted

    # ── artifacts ────────────────────────────────────────────

    def list_artifacts(self) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, insight_id, name, description, data_source, data, created_at FROM artifacts ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        self.conn.rollback()

        summaries = []
        for row in rows:
            d = self._artifact_row_to_dict(row)
            viz = d.get("visualization", {})
            if viz.get("type") == "report":
                viz_type = "report"
            elif "nodes" in viz or "edges" in viz:
                viz_type = "graph"
            else:
                viz_type = "chart"

            summaries.append({
                "id": d["id"],
                "name": d["name"],
                "description": d.get("description", ""),
                "createdAt": d["createdAt"],
                "dataSource": d["dataSource"],
                "visualizationType": viz_type,
            })
        return summaries

    def get_artifact(self, artifact_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, insight_id, name, description, data_source, data, created_at FROM artifacts WHERE id = %s",
                (artifact_id,),
            )
            row = cur.fetchone()
        self.conn.rollback()
        if row is None:
            return None
        return self._artifact_row_to_dict(row)

    def create_artifact(
        self, session_id: str, insight_id: str, name: str, description: str
    ) -> dict | None:
        session = self.get_session(session_id)
        if session is None:
            return None

        insight = None
        for i in session.get("insights", []):
            if i["id"] == insight_id:
                insight = i
                break
        if insight is None:
            return None

        visualization = insight.get("visualization", {})
        data_snapshot = self._create_data_snapshot(visualization)

        artifact_id = self._generate_id()
        now = self._now_iso()
        artifact_data = {
            "visualization": visualization,
            "dataSnapshot": data_snapshot,
        }

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO artifacts (id, session_id, insight_id, name, description, data_source, data, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, insight_id, name, description, data_source, data, created_at
                """,
                (artifact_id, session_id, insight_id, name, description, session["dataSource"], json.dumps(artifact_data), now),
            )
            row = cur.fetchone()
        self.conn.commit()

        # Update insight's savedAsArtifact
        self.update_session(
            session_id, {"updateInsight": {"id": insight_id, "savedAsArtifact": artifact_id}}
        )

        return self._artifact_row_to_dict(row)

    def create_report_artifact(
        self,
        session_id: str,
        title: str,
        description: str,
        visualization: dict,
        data_snapshot: dict,
    ) -> dict | None:
        session = self.get_session(session_id)
        if session is None:
            return None

        artifact_id = self._generate_id()
        now = self._now_iso()
        artifact_data = {
            "visualization": visualization,
            "dataSnapshot": data_snapshot,
        }

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO artifacts (id, session_id, insight_id, name, description, data_source, data, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, insight_id, name, description, data_source, data, created_at
                """,
                (artifact_id, session_id, None, title, description, session["dataSource"], json.dumps(artifact_data), now),
            )
            row = cur.fetchone()
        self.conn.commit()
        return self._artifact_row_to_dict(row)

    def delete_artifact(self, artifact_id: str) -> bool:
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return False

        # Try to clear reference from insight
        session_id = artifact.get("sessionId")
        insight_id = artifact.get("insightId")
        if session_id and insight_id:
            session = self.get_session(session_id)
            if session:
                self.update_session(
                    session_id, {"updateInsight": {"id": insight_id, "savedAsArtifact": None}}
                )

        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM artifacts WHERE id = %s", (artifact_id,))
        self.conn.commit()
        return True

    # ── row converters ───────────────────────────────────────

    def _session_row_to_dict(self, row) -> dict:
        """Convert a sessions table row to the dict shape routers expect."""
        data = row[4]
        if isinstance(data, str):
            data = json.loads(data)

        # Ensure memory always present
        if "memory" not in data:
            data["memory"] = {
                "facts": [],
                "preferences": [],
                "corrections": [],
                "conclusions": [],
            }

        result = {
            "id": row[0],
            "name": row[1],
            "dataSource": row[2],
            "createdBy": row[3],
            "createdAt": self._ts(row[5]),
            "updatedAt": self._ts(row[6]),
        }
        # Merge nested JSONB data into top-level
        result["messages"] = data.get("messages", [])
        result["insights"] = data.get("insights", [])
        result["datasets"] = data.get("datasets", [])
        result["memory"] = data["memory"]
        if "historySummary" in data:
            result["historySummary"] = data["historySummary"]
        if "historySummaryUpToIndex" in data:
            result["historySummaryUpToIndex"] = data["historySummaryUpToIndex"]
        return result

    def _artifact_row_to_dict(self, row) -> dict:
        """Convert an artifacts table row to the dict shape routers expect."""
        data = row[6]
        if isinstance(data, str):
            data = json.loads(data)

        return {
            "id": row[0],
            "sessionId": row[1],
            "insightId": row[2],
            "name": row[3],
            "description": row[4],
            "dataSource": row[5],
            "visualization": data.get("visualization", {}),
            "dataSnapshot": data.get("dataSnapshot", {}),
            "createdAt": self._ts(row[7]),
        }

    @staticmethod
    def _create_data_snapshot(visualization: dict) -> dict:
        data = visualization.get("data", [])
        columns = []
        if data and isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                columns = list(data[0].keys())
        return {
            "data": data,
            "columns": columns,
            "rowCount": len(data) if isinstance(data, list) else 0,
            "capturedAt": datetime.now(UTC).isoformat(),
        }
