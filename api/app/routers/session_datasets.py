"""Session-Dataset linking endpoints."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers.datasets import get_dataset_storage, get_database_url
from app.storage.dataset_storage import DatasetStorage
from app.storage.file_storage import FileStorage

router = APIRouter(prefix="/api/sessions", tags=["session-datasets"])


class AttachDatasetRequest(BaseModel):
    dataset_id: str


@router.post("/{session_id}/datasets")
def attach_dataset(
    session_id: str,
    request: AttachDatasetRequest,
    storage: FileStorage = Depends(get_storage),
    dataset_storage: DatasetStorage = Depends(get_dataset_storage),
):
    """Attach a dataset to a session."""
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    dataset = dataset_storage.get_dataset(request.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    updated = storage.update_session(session_id, {"addDataset": request.dataset_id})
    return {"datasets": updated.get("datasets", [])}


@router.delete("/{session_id}/datasets/{dataset_id}")
def detach_dataset(
    session_id: str,
    dataset_id: str,
    storage: FileStorage = Depends(get_storage),
):
    """Detach a dataset from a session."""
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    updated = storage.update_session(session_id, {"removeDataset": dataset_id})
    return {"datasets": updated.get("datasets", [])}


@router.get("/{session_id}/datasets")
def list_session_datasets(
    session_id: str,
    storage: FileStorage = Depends(get_storage),
    dataset_storage: DatasetStorage = Depends(get_dataset_storage),
):
    """List datasets attached to a session."""
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    dataset_ids = session.get("datasets", [])
    datasets = []
    for ds_id in dataset_ids:
        ds = dataset_storage.get_dataset(ds_id)
        if ds is not None:
            datasets.append(ds)

    return {"datasets": datasets}


class DerivedTable(BaseModel):
    """A derived table created by the agent during a session."""
    name: str
    pg_table_name: str
    row_count: int
    columns: list[str]
    dtypes: dict[str, str]


@router.get("/{session_id}/derived-tables")
def list_derived_tables(
    session_id: str,
    storage: FileStorage = Depends(get_storage),
    database_url: str = Depends(get_database_url),
):
    """
    List derived tables created during this session.

    Derived tables have names like _derived_{session_id}_{table_name}.
    These are ephemeral tables created by the agent that can be promoted to datasets.
    """
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    derived_tables: list[dict] = []

    try:
        conn = psycopg.connect(database_url, autocommit=True)
        try:
            with conn.cursor() as cur:
                # Find all derived tables for this session
                pattern = f"_derived_{session_id}_%"
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name LIKE %s
                    ORDER BY table_name
                """, (pattern,))
                table_names = [row[0] for row in cur.fetchall()]

                # Get metadata for each table
                for pg_table_name in table_names:
                    # Extract short name (after _derived_{session_id}_)
                    prefix = f"_derived_{session_id}_"
                    short_name = pg_table_name[len(prefix):]

                    # Get column info
                    cur.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position
                    """, (pg_table_name,))
                    columns_info = cur.fetchall()

                    # Get row count
                    cur.execute(f'SELECT COUNT(*) FROM "{pg_table_name}"')
                    row_count = cur.fetchone()[0]

                    derived_tables.append({
                        "name": short_name,
                        "pg_table_name": pg_table_name,
                        "row_count": row_count,
                        "columns": [col[0] for col in columns_info],
                        "dtypes": {col[0]: col[1] for col in columns_info},
                    })
        finally:
            conn.close()
    except Exception:
        # If PostgreSQL is unavailable, return empty list
        pass

    return {"derived_tables": derived_tables}
