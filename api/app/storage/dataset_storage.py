"""Dataset metadata storage in PostgreSQL."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import psycopg


class DatasetStorage:
    """Stores dataset metadata in a PostgreSQL table."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._conn: Optional[psycopg.Connection] = None

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._database_url, autocommit=False)
        return self._conn

    def initialize(self) -> None:
        """Create the datasets table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL DEFAULT 'anonymous',
                    visibility TEXT NOT NULL DEFAULT 'private',
                    derived_from TEXT,
                    tables JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        self.conn.commit()

    def create_dataset(
        self,
        name: str,
        owner: str = "anonymous",
        visibility: str = "private",
        derived_from: str | None = None,
    ) -> dict:
        """Create a new dataset record."""
        dataset_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO datasets (id, name, owner, visibility, derived_from, tables, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, owner, visibility, derived_from, tables, created_at, updated_at
                """,
                (dataset_id, name, owner, visibility, derived_from, json.dumps([]), now, now),
            )
            row = cur.fetchone()
        self.conn.commit()
        return self._row_to_dict(row)

    def get_dataset(self, dataset_id: str) -> dict | None:
        """Get a dataset by ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, owner, visibility, derived_from, tables, created_at, updated_at FROM datasets WHERE id = %s",
                (dataset_id,),
            )
            row = cur.fetchone()
        self.conn.rollback()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_datasets(
        self,
        owner: str | None = None,
        visibility: str | None = None,
    ) -> list[dict]:
        """List datasets with optional filters."""
        conditions = []
        params: list = []

        if owner is not None:
            conditions.append("owner = %s")
            params.append(owner)
        if visibility is not None:
            conditions.append("visibility = %s")
            params.append(visibility)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT id, name, owner, visibility, derived_from, tables, created_at, updated_at FROM datasets {where} ORDER BY created_at DESC",
                params,
            )
            rows = cur.fetchall()
        self.conn.rollback()
        return [self._row_to_dict(row) for row in rows]

    def update_dataset(self, dataset_id: str, **kwargs) -> dict | None:
        """Update dataset fields (name, visibility)."""
        allowed = {"name", "visibility"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}

        if not updates:
            return self.get_dataset(dataset_id)

        set_clauses = [f"{k} = %s" for k in updates]
        set_clauses.append("updated_at = %s")
        values = list(updates.values())
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(dataset_id)

        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE datasets SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, owner, visibility, derived_from, tables, created_at, updated_at",
                values,
            )
            row = cur.fetchone()
        self.conn.commit()
        if row is None:
            return None
        return self._row_to_dict(row)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset record."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def add_table(
        self,
        dataset_id: str,
        name: str,
        pg_table_name: str,
        row_count: int = 0,
        columns: list[str] | None = None,
        dtypes: dict[str, str] | None = None,
    ) -> dict | None:
        """Add a table entry to a dataset's tables list."""
        table_info = {
            "name": name,
            "pg_table_name": pg_table_name,
            "row_count": row_count,
            "columns": columns or [],
            "dtypes": dtypes or {},
        }

        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE datasets
                SET tables = tables || %s::jsonb,
                    updated_at = %s
                WHERE id = %s
                RETURNING id, name, owner, visibility, derived_from, tables, created_at, updated_at
                """,
                (json.dumps([table_info]), datetime.now(timezone.utc).isoformat(), dataset_id),
            )
            row = cur.fetchone()
        self.conn.commit()
        if row is None:
            return None
        return self._row_to_dict(row)

    def _row_to_dict(self, row) -> dict:
        """Convert a database row to a dict."""
        tables = row[5]
        if isinstance(tables, str):
            tables = json.loads(tables)

        created_at = row[6]
        updated_at = row[7]
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()

        return {
            "id": row[0],
            "name": row[1],
            "owner": row[2],
            "visibility": row[3],
            "derived_from": row[4],
            "tables": tables,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def ensure_prebuilt_datasets(self) -> None:
        """Create Dataset records for pre-built data sources (idempotent)."""
        from app.data.sources import DATA_SOURCES

        existing = self.list_datasets(owner="system")
        existing_names = {ds["name"] for ds in existing}

        for source_id, info in DATA_SOURCES.items():
            if info["name"] not in existing_names:
                # Discover tables for this data source
                tables = self._discover_source_tables(source_id, info)

                if tables:  # Only create if tables exist
                    dataset = self.create_dataset(
                        name=info["name"],
                        owner="system",
                        visibility="public",
                    )
                    # Add discovered tables to the dataset
                    for table_info in tables:
                        self.add_table(
                            dataset_id=dataset["id"],
                            name=table_info["name"],
                            pg_table_name=table_info["pg_table_name"],
                            row_count=table_info["row_count"],
                            columns=table_info["columns"],
                            dtypes=table_info["dtypes"],
                        )

    def _discover_source_tables(self, source_id: str, source_info: dict) -> list[dict]:
        """
        Discover tables for a data source from PostgreSQL.

        Returns table metadata in Dataset tables format.
        """
        if self._conn is None or self._conn.closed:
            return []

        # Map source IDs to their table patterns
        source_patterns = {
            'vndb': ['vn', 'staff', 'producers', 'characters', 'tags', 'traits', 'releases', 'vn_'],
            'vndb_collaboration': ['staff_', 'vn_staff'],
            'steam': ['games', 'reviews', 'achievements', 'steam_'],
            'polymarket': ['markets', 'bets', 'outcomes', 'polymarket_'],
        }

        patterns = source_patterns.get(source_id, [])
        if not patterns:
            return []

        try:
            with self.conn.cursor() as cur:
                # Get all tables from information_schema
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_type = 'BASE TABLE'
                      AND table_name NOT LIKE '_dataset_%%'
                      AND table_name NOT LIKE '_derived_%%'
                    ORDER BY table_name
                """)
                all_tables = [row[0] for row in cur.fetchall()]

                # Filter to tables relevant to this source
                relevant_tables = []
                for table_name in all_tables:
                    # Include if table name matches any pattern
                    for pattern in patterns:
                        if table_name.lower().startswith(pattern) or table_name.lower() == pattern:
                            relevant_tables.append(table_name)
                            break

                # Get metadata for each table
                tables_metadata = []
                for table_name in relevant_tables:
                    # Get column info
                    cur.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns_info = cur.fetchall()

                    # Get row count
                    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    row_count = cur.fetchone()[0]

                    tables_metadata.append({
                        "name": table_name,
                        "pg_table_name": table_name,  # No prefix for source tables
                        "row_count": row_count,
                        "columns": [col[0] for col in columns_info],
                        "dtypes": {col[0]: col[1] for col in columns_info},
                    })

            self.conn.rollback()
            return tables_metadata

        except Exception as e:
            self.conn.rollback()
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to discover tables for {source_id}: {e}"
            )
            return []

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
