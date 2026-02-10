"""CSV upload service — parse, validate, load into PostgreSQL."""

import io
import re
from pathlib import Path

import pandas as pd
import psycopg


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_COLUMNS = 500


def parse_csv(content: bytes) -> pd.DataFrame:
    """Parse CSV bytes into a pandas DataFrame with type inference."""
    return pd.read_csv(io.BytesIO(content))


def sanitize_table_name(filename: str) -> str:
    """Convert a filename into a valid PostgreSQL table identifier."""
    name = Path(filename).stem
    # Lowercase
    name = name.lower()
    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^a-z0-9_]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores
    name = name.strip("_")
    # Prefix with underscore if starts with digit
    if name and name[0].isdigit():
        name = f"_{name}"
    # Fallback
    if not name:
        name = "unnamed_table"
    return name


def validate_csv(df: pd.DataFrame) -> list[str]:
    """Validate a parsed DataFrame. Returns list of error messages (empty = valid)."""
    errors = []
    if df.empty or len(df.columns) == 0:
        errors.append("CSV file is empty or has no columns")
    if len(df.columns) > MAX_COLUMNS:
        errors.append(f"Too many columns ({len(df.columns)}). Maximum is {MAX_COLUMNS}.")
    return errors


def load_dataframe_to_pg(
    df: pd.DataFrame,
    pg_table_name: str,
    database_url: str,
) -> int:
    """
    Load a DataFrame into PostgreSQL as a new table.

    Returns the number of rows inserted.
    """
    conn = psycopg.connect(database_url, autocommit=False)
    try:
        with conn.cursor() as cur:
            # Build column definitions
            col_defs = []
            for col in df.columns:
                pg_type = _pandas_dtype_to_pg(df[col].dtype)
                safe_col = f'"{col}"'
                col_defs.append(f"{safe_col} {pg_type}")

            cur.execute(f'DROP TABLE IF EXISTS "{pg_table_name}"')
            cur.execute(f'CREATE TABLE "{pg_table_name}" ({", ".join(col_defs)})')

            # Use COPY for fast bulk insert
            with cur.copy(f'COPY "{pg_table_name}" FROM STDIN') as copy:
                for row in df.itertuples(index=False):
                    copy.write_row(row)

            conn.commit()
            return len(df)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _pandas_dtype_to_pg(dtype) -> str:
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
