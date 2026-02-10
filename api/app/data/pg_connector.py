"""PostgreSQL-based connector for querying data via SQL."""

from typing import Optional

import pandas as pd
import psycopg


class PostgreSQLConnector:
    """
    Query engine using PostgreSQL.

    Connects to a database where source data is already loaded.
    Supports derived tables for multi-step analysis.
    """

    def __init__(self, database_url: str, session_id: Optional[str] = None, dataset_ids: list[str] | None = None):
        self._database_url = database_url
        self._session_id = session_id or "default"
        self._derived_prefix = f"_derived_{self._session_id}_"
        self._derived_tables: list[str] = []
        self._dataset_ids = dataset_ids or []
        self._dataset_tables: dict[str, str] = {}  # short_name → pg_table_name
        self._conn: Optional[psycopg.Connection] = None

    @property
    def conn(self) -> psycopg.Connection:
        """Lazy-init PostgreSQL connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._database_url, autocommit=False)
        return self._conn

    def list_tables(self) -> list[str]:
        """List tables available to this session (from attached datasets only).

        Returns only tables from explicitly attached datasets.
        No datasets attached = no tables available.
        """
        self._discover_dataset_tables()
        self._discover_derived_tables()
        return sorted(self._dataset_tables.keys())

    def _discover_dataset_tables(self) -> None:
        """Discover dataset tables in PG for attached dataset_ids."""
        if not self._dataset_ids:
            return
        self._dataset_tables = {}
        with self.conn.cursor() as cur:
            for ds_id in self._dataset_ids:
                prefix = f"_dataset_{ds_id}_"
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE %s",
                    (f"{prefix}%",),
                )
                for (pg_name,) in cur.fetchall():
                    short_name = pg_name[len(prefix):]
                    self._dataset_tables[short_name] = pg_name
        self.conn.rollback()

    def _discover_derived_tables(self) -> None:
        """Discover derived tables from previous turns via information_schema."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE %s",
                (f"{self._derived_prefix}%",),
            )
            for (pg_name,) in cur.fetchall():
                short_name = pg_name[len(self._derived_prefix):]
                if short_name not in self._derived_tables:
                    self._derived_tables.append(short_name)
        self.conn.rollback()

    def list_derived_tables(self) -> list[str]:
        """List agent-created derived tables for this session."""
        self._discover_derived_tables()
        return list(self._derived_tables)

    def get_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Load a table as DataFrame."""
        actual_name = table_name
        if table_name in self._derived_tables:
            actual_name = f"{self._derived_prefix}{table_name}"
        elif table_name in self._dataset_tables:
            actual_name = self._dataset_tables[table_name]

        limit_clause = f" LIMIT {limit}" if limit else ""
        try:
            with self.conn.cursor() as cur:
                cur.execute(f'SELECT * FROM "{actual_name}"{limit_clause}')
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
            self.conn.rollback()
            return pd.DataFrame(data, columns=columns)
        except Exception:
            self.conn.rollback()
            raise

    def execute_sql(self, sql: str) -> dict:
        """
        Execute SQL. Returns result data + tracks any new tables created.

        The agent writes SQL using short names (e.g., "my_analysis").
        Internally, derived tables are prefixed with session ID for isolation.

        Table access is restricted to:
        - Tables from attached datasets
        - Derived tables created during the session

        Returns dict with:
        - data: list of records (for SELECT)
        - columns: list of column names
        - row_count: number of rows
        - created_table: short name of table if CREATE was used

        Raises:
        - PermissionError: If SQL references tables not in attached datasets
        """
        sql_stripped = sql.strip()
        sql_upper = sql_stripped.upper()

        # Discover tables first (needed for access check)
        self._discover_dataset_tables()
        self._discover_derived_tables()

        # Detect CREATE TABLE to track it
        created_table = None
        if sql_upper.startswith("CREATE") and "TABLE" in sql_upper:
            created_table = self._extract_table_name(sql_stripped)
            if created_table:
                prefixed_name = f"{self._derived_prefix}{created_table}"
                sql_stripped = sql_stripped.replace(created_table, f'"{prefixed_name}"', 1)

        # Validate table access before rewriting
        self._validate_table_access(sql_stripped, created_table)

        # Rewrite short names to prefixed names
        sql_stripped = self._rewrite_derived_refs(sql_stripped)

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql_stripped)

                # Track derived table
                if created_table and created_table not in self._derived_tables:
                    self._derived_tables.append(created_table)

                # For CREATE/INSERT/DROP statements, no result set
                if cur.description is None:
                    self.conn.commit()
                    return {
                        "data": [],
                        "columns": [],
                        "row_count": 0,
                        "created_table": created_table,
                        "message": (
                            f"Table '{created_table}' created successfully"
                            if created_table
                            else "Statement executed"
                        ),
                    }

                # For SELECT statements, return data
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                self.conn.commit()
                return {
                    "data": data,
                    "columns": columns,
                    "row_count": len(data),
                }
        except Exception:
            self.conn.rollback()
            raise

    def _extract_table_name(self, sql: str) -> Optional[str]:
        """Extract table name from CREATE TABLE statement."""
        parts = sql.split()
        for i, part in enumerate(parts):
            if part.upper() == "TABLE":
                if i + 1 < len(parts):
                    name = parts[i + 1].strip('"').strip("'")
                    if name.upper() == "IF":
                        # CREATE TABLE IF NOT EXISTS <name>
                        if i + 4 < len(parts):
                            return parts[i + 4].strip('"').strip("'").rstrip("(")
                    elif name.upper() in ("TEMP", "TEMPORARY"):
                        # CREATE TEMP TABLE <name>
                        if i + 2 < len(parts):
                            next_word = parts[i + 2].strip('"').strip("'")
                            if next_word.upper() == "TABLE":
                                # CREATE TEMPORARY TABLE <name>
                                if i + 3 < len(parts):
                                    return parts[i + 3].strip('"').strip("'").rstrip("(")
                            else:
                                return next_word.rstrip("(")
                    else:
                        return name.rstrip("(")
        return None

    def _rewrite_derived_refs(self, sql: str) -> str:
        """Replace short derived/dataset table names with prefixed names in SQL."""
        import re

        for short_name in self._derived_tables:
            prefixed = f"{self._derived_prefix}{short_name}"
            if short_name in sql and prefixed not in sql:
                sql = re.sub(
                    r'(?<![.\w])' + re.escape(short_name) + r'(?!\w)',
                    f'"{prefixed}"',
                    sql,
                )
        for short_name, pg_name in self._dataset_tables.items():
            if short_name in sql and pg_name not in sql:
                sql = re.sub(
                    r'(?<![.\w])' + re.escape(short_name) + r'(?!\w)',
                    f'"{pg_name}"',
                    sql,
                )
        return sql

    def _validate_table_access(self, sql: str, created_table: str | None = None) -> None:
        """Validate that SQL only references allowed tables.

        Allowed tables are:
        - Tables from attached datasets
        - Derived tables created during the session
        - The table being created (for CREATE TABLE statements)

        Raises:
            PermissionError: If SQL references unauthorized tables
        """
        import re

        # Build set of allowed table names
        allowed = set(self._dataset_tables.keys()) | set(self._derived_tables)

        # Also allow prefixed versions
        allowed |= set(self._dataset_tables.values())
        allowed |= {f"{self._derived_prefix}{t}" for t in self._derived_tables}

        # If creating a new table, allow it
        if created_table:
            allowed.add(created_table)
            allowed.add(f"{self._derived_prefix}{created_table}")

        # Allow CTE names (WITH name AS (...), or comma-separated)
        cte_pattern = r'(?:WITH(?:\s+RECURSIVE)?|,)\s+(\w+)\s+AS\s*\('
        allowed |= set(re.findall(cte_pattern, sql, re.IGNORECASE))

        # Remove EXTRACT(...FROM...) to avoid false positives
        # EXTRACT(YEAR FROM col) has FROM inside a function, not a table ref
        sql_cleaned = re.sub(r'EXTRACT\s*\([^)]*\)', '', sql, flags=re.IGNORECASE)

        # Extract potential table references from SQL
        # Look for identifiers after FROM, JOIN, INTO, UPDATE, TABLE keywords
        table_pattern = r'(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(?:IF\s+NOT\s+EXISTS\s+)?["\']?(\w+)["\']?'
        referenced = {t.strip('"') for t in re.findall(table_pattern, sql_cleaned, re.IGNORECASE)}

        # Filter out SQL keywords that might be captured
        sql_keywords = {
            'SELECT', 'WHERE', 'AND', 'OR', 'ON', 'AS', 'SET', 'VALUES',
            'NULL', 'NOT', 'EXISTS', 'IN', 'LIKE',
            # SQL types and functions that appear after FROM/TABLE in valid SQL
            'CAST', 'EXTRACT', 'LATERAL', 'UNNEST', 'GENERATE_SERIES',
            'INFORMATION_SCHEMA', 'PG_CATALOG',
            # Date/time keywords that EXTRACT uses
            'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'EPOCH',
            'DOW', 'DOY', 'QUARTER', 'WEEK',
        }
        referenced = {t for t in referenced if t.upper() not in sql_keywords}

        # Check for unauthorized access
        unauthorized = referenced - allowed

        # Filter out tables that start with allowed prefixes (they're internal)
        unauthorized = {t for t in unauthorized if not t.startswith('_derived_') and not t.startswith('_dataset_')}

        if unauthorized:
            raise PermissionError(
                f"Access denied to tables: {', '.join(sorted(unauthorized))}. "
                f"Only tables from attached datasets are accessible."
            )

    def get_schema(self, include_derived: bool = True) -> dict:
        """Get schema for tables available to this session.

        Only returns tables from attached datasets + derived tables.
        No datasets attached = empty schema.
        """
        self._discover_dataset_tables()
        self._discover_derived_tables()
        schema: dict = {
            "tables": {},
            "derived_tables": {},
        }

        # Only show tables from attached datasets
        for short_name, pg_name in self._dataset_tables.items():
            schema["tables"][short_name] = self._get_table_schema(pg_name)

        # Add derived tables (agent-created during analysis)
        if include_derived:
            for short_name in self._derived_tables:
                prefixed = f"{self._derived_prefix}{short_name}"
                schema["derived_tables"][short_name] = self._get_table_schema(prefixed)

        return schema

    def _get_table_schema(self, name: str) -> dict:
        """Get schema for a single table."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (name,),
                )
                cols = cur.fetchall()

                cur.execute(f'SELECT COUNT(*) FROM "{name}"')
                row_count = cur.fetchone()[0]

            self.conn.rollback()
            return {
                "columns": [c[0] for c in cols],
                "dtypes": {c[0]: c[1] for c in cols},
                "row_count": row_count,
            }
        except Exception:
            self.conn.rollback()
            return {"error": "Could not read schema"}

    def register_dataframe(self, name: str, df: pd.DataFrame) -> None:
        """Insert a pandas DataFrame as a queryable table."""
        prefixed = f"{self._derived_prefix}{name}"

        with self.conn.cursor() as cur:
            col_defs = []
            for col in df.columns:
                pg_type = self._pandas_dtype_to_pg(df[col].dtype)
                col_defs.append(f'"{col}" {pg_type}')

            cur.execute(f'DROP TABLE IF EXISTS "{prefixed}"')
            cur.execute(f'CREATE TABLE "{prefixed}" ({", ".join(col_defs)})')

            with cur.copy(f'COPY "{prefixed}" FROM STDIN') as copy:
                for row in df.itertuples(index=False):
                    copy.write_row(row)

            self.conn.commit()

        if name not in self._derived_tables:
            self._derived_tables.append(name)

    def _pandas_dtype_to_pg(self, dtype) -> str:
        """Map pandas dtype to PostgreSQL type."""
        dtype_str = str(dtype)
        if "int" in dtype_str:
            return "BIGINT"
        elif "float" in dtype_str:
            return "DOUBLE PRECISION"
        elif "bool" in dtype_str:
            return "BOOLEAN"
        elif "datetime" in dtype_str:
            return "TIMESTAMP"
        else:
            return "TEXT"

    def cleanup_session(self) -> None:
        """Drop all derived tables for this session."""
        self._discover_derived_tables()
        try:
            with self.conn.cursor() as cur:
                for short_name in self._derived_tables:
                    prefixed = f"{self._derived_prefix}{short_name}"
                    cur.execute(f'DROP TABLE IF EXISTS "{prefixed}"')
                self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
        self._derived_tables.clear()

    def close(self) -> None:
        """Close the connection without dropping derived tables.

        Derived tables persist until session deletion (cleanup_session is called explicitly).
        """
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
