"""
Schema Generator - Generates ER diagram specs from PostgreSQL.
"""

from datetime import UTC, datetime

import psycopg

from app.config import get_settings


class SchemaGenerator:
    """Generates ERDiagramSpec from PostgreSQL database."""

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or get_settings().database_url

    def generate(self, source_id: str, dataset_ids: list[str] | None = None) -> dict:
        """
        Generate ERDiagramSpec for a data source.

        Args:
            source_id: Data source identifier (currently ignored — all tables
                       come from the single PostgreSQL database)
            dataset_ids: Optional list of dataset IDs to filter tables.
                        When provided, only tables matching `_dataset_{id}_*` are included.

        Returns:
            ERDiagramSpec dict with tables, relationships, metadata

        Raises:
            ValueError: If source_id is empty
        """
        if not source_id:
            raise ValueError("Data source ID cannot be empty")

        conn = psycopg.connect(self._database_url, autocommit=True)
        try:
            tables = self._get_tables(conn, dataset_ids=dataset_ids)
            relationships = self._get_relationships(conn)
            pk_columns = self._get_primary_keys(conn)
            fk_columns = self._get_foreign_key_columns(conn)

            # Post-filter relationships, PKs, FKs to only matched tables
            table_name_set = {t["name"] for t in tables}
            if dataset_ids:
                relationships = [
                    r for r in relationships
                    if r["from"].split(".")[0] in table_name_set
                    and r["to"].split(".")[0] in table_name_set
                ]
                pk_columns = {
                    k: v for k, v in pk_columns.items() if k in table_name_set
                }
                fk_columns = {
                    k: v for k, v in fk_columns.items() if k in table_name_set
                }

            # Mark PKs and FKs on columns
            for table in tables:
                table_pks = pk_columns.get(table["name"], set())
                table_fks = fk_columns.get(table["name"], {})
                for col in table["columns"]:
                    col["isPrimaryKey"] = col["name"] in table_pks
                    col["isForeignKey"] = col["name"] in table_fks
                    col["references"] = table_fks.get(col["name"])

            return {
                "dataSource": source_id,
                "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "tables": tables,
                "relationships": relationships,
            }
        finally:
            conn.close()

    def _get_tables(
        self, conn: psycopg.Connection, dataset_ids: list[str] | None = None
    ) -> list[dict]:
        """Get public tables with columns and row counts.

        Args:
            dataset_ids: When provided, only return tables matching
                        `_dataset_{id}_%` for each ID.
        """
        tables = []

        with conn.cursor() as cur:
            if dataset_ids:
                # Build LIKE patterns for each dataset ID
                patterns = [f"_dataset_{did}_%" for did in dataset_ids]
                conditions = " OR ".join(
                    "table_name LIKE %s" for _ in patterns
                )
                cur.execute(
                    f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND ({conditions})
                    ORDER BY table_name
                    """,
                    patterns,
                )
            else:
                # Get all non-derived tables
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name NOT LIKE '_derived_%%'
                    ORDER BY table_name
                """)
            table_names = [row[0] for row in cur.fetchall()]

            for table_name in table_names:
                # Get columns
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "isPrimaryKey": False,
                        "isForeignKey": False,
                        "references": None,
                    }
                    for row in cur.fetchall()
                ]

                # Get row count
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                row_count = cur.fetchone()[0]

                tables.append({
                    "name": table_name,
                    "columns": columns,
                    "rowCount": row_count,
                })

        return tables

    def _get_primary_keys(self, conn: psycopg.Connection) -> dict[str, set[str]]:
        """Get primary key columns per table. Returns {table_name: {col_names}}."""
        result: dict[str, set[str]] = {}

        with conn.cursor() as cur:
            cur.execute("""
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
            """)
            for table_name, col_name in cur.fetchall():
                result.setdefault(table_name, set()).add(col_name)

        return result

    def _get_foreign_key_columns(self, conn: psycopg.Connection) -> dict[str, dict[str, str]]:
        """Get FK columns per table. Returns {table: {col: 'ref_table.ref_col'}}."""
        result: dict[str, dict[str, str]] = {}

        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS ref_table,
                    ccu.column_name AS ref_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                  AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
            """)
            for table_name, col_name, ref_table, ref_col in cur.fetchall():
                result.setdefault(table_name, {})[col_name] = f"{ref_table}.{ref_col}"

        return result

    def _get_relationships(self, conn: psycopg.Connection) -> list[dict]:
        """Get all foreign key relationships."""
        relationships = []

        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS ref_table,
                    ccu.column_name AS ref_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                  AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
            """)
            for table_name, col_name, ref_table, ref_col in cur.fetchall():
                relationships.append({
                    "from": f"{table_name}.{col_name}",
                    "to": f"{ref_table}.{ref_col}",
                    "type": "many-to-one",
                })

        return relationships
