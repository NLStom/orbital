"""
Dataset API endpoints.

CRUD for datasets + CSV file upload.
"""

import logging
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.agent.auto_profile import generate_table_profile, generate_suggested_questions
from app.config import get_settings
from app.data.loader import DataLoader
from app.schemas.datasets import Dataset, DatasetListResponse, DatasetUpdate
from app.services.csv_upload import (
    MAX_FILE_SIZE,
    load_dataframe_to_pg,
    parse_csv,
    sanitize_table_name,
    validate_csv,
)
from app.storage.dataset_storage import DatasetStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# --- Dependencies ---

_dataset_storage: DatasetStorage | None = None


def get_dataset_storage() -> DatasetStorage:
    """Get DatasetStorage singleton."""
    global _dataset_storage
    if _dataset_storage is None:
        settings = get_settings()
        _dataset_storage = DatasetStorage(database_url=settings.database_url)
        _dataset_storage.initialize()
    return _dataset_storage


def get_database_url() -> str:
    """Get database URL from settings."""
    return get_settings().database_url


# --- Endpoints ---


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=Dataset)
async def upload_dataset(
    files: list[UploadFile] = File(...),
    name: Optional[str] = Form(default=None),
    session_id: Optional[str] = Form(default=None),
    storage: DatasetStorage = Depends(get_dataset_storage),
    database_url: str = Depends(get_database_url),
):
    """
    Upload one or more CSV files as a new dataset.

    - Multiple files become multiple tables in one dataset.
    - Dataset name defaults to first filename if not provided.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Parse and validate all files first
    parsed_files = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB",
            )
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"File '{f.filename}' is empty")

        try:
            df = parse_csv(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse '{f.filename}': {e}")

        errors = validate_csv(df)
        if errors:
            raise HTTPException(status_code=400, detail=f"Validation error in '{f.filename}': {'; '.join(errors)}")

        table_name = sanitize_table_name(f.filename or "unnamed")
        parsed_files.append((table_name, df, f.filename))

    # Create dataset record
    dataset_name = name or parsed_files[0][0]
    dataset = storage.create_dataset(name=dataset_name)
    dataset_id = dataset["id"]

    # Load each file into PG and register in dataset
    for table_name, df, filename in parsed_files:
        pg_table_name = f"_dataset_{dataset_id}_{table_name}"

        try:
            row_count = load_dataframe_to_pg(
                df=df,
                pg_table_name=pg_table_name,
                database_url=database_url,
            )
        except Exception as e:
            logger.error(f"Failed to load '{filename}' into PG: {e}")
            # Clean up: delete dataset record
            storage.delete_dataset(dataset_id)
            raise HTTPException(status_code=500, detail=f"Failed to load '{filename}' into database")

        columns = list(df.columns)
        dtypes = {col: _pandas_dtype_to_pg_label(df[col].dtype) for col in columns}
        storage.add_table(
            dataset_id=dataset_id,
            name=table_name,
            pg_table_name=pg_table_name,
            row_count=row_count,
            columns=columns,
            dtypes=dtypes,
        )

    # Generate profile and suggested questions for first table
    suggested_questions: list[str] = []
    if parsed_files:
        try:
            first_table = parsed_files[0]
            first_table_name = first_table[0]
            pg_table_name = f"_dataset_{dataset_id}_{first_table_name}"

            # Create DataLoader to access the table
            data_loader = DataLoader(database_url=database_url)
            profile = generate_table_profile(data_loader, pg_table_name, display_name=first_table_name)
            suggested_questions = generate_suggested_questions(profile)
        except Exception as e:
            logger.warning(f"Failed to generate profile/questions: {e}")
            # Don't fail upload if profiling fails

    # Get dataset from storage and add suggested questions
    dataset_dict = storage.get_dataset(dataset_id)
    if dataset_dict:
        # Convert to Dataset model with suggested_questions
        dataset = Dataset(
            **dataset_dict,
            quality_reports=None,  # Quality reports not yet implemented in upload
            suggested_questions=suggested_questions if suggested_questions else None
        )
        return dataset

    # Fallback if dataset not found (shouldn't happen)
    raise HTTPException(status_code=500, detail="Failed to retrieve uploaded dataset")


MAX_PREVIEW_LIMIT = 1000


@router.get("/{dataset_id}/tables/{table_name}/preview")
def preview_table(
    dataset_id: str,
    table_name: str,
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    storage: DatasetStorage = Depends(get_dataset_storage),
    database_url: str = Depends(get_database_url),
):
    """
    Preview rows from a dataset table.

    Returns paginated rows with column names.
    """
    dataset = storage.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Find table in dataset
    table_info = None
    for t in dataset["tables"]:
        if t["name"] == table_name:
            table_info = t
            break

    if table_info is None:
        raise HTTPException(status_code=404, detail="Table not found in dataset")

    # Clamp limit
    limit = min(limit, MAX_PREVIEW_LIMIT)

    pg_table_name = table_info["pg_table_name"]

    conn = psycopg.connect(database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT * FROM "{pg_table_name}" LIMIT %s OFFSET %s',
                (limit, offset),
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

    return {
        "columns": columns,
        "data": data,
        "total_rows": table_info["row_count"],
        "limit": limit,
        "offset": offset,
    }


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    visibility: Optional[str] = None,
    storage: DatasetStorage = Depends(get_dataset_storage),
):
    """List datasets with optional visibility filter."""
    datasets = storage.list_datasets(visibility=visibility)
    # Convert to summary format
    summaries = []
    for ds in datasets:
        summaries.append({
            "id": ds["id"],
            "name": ds["name"],
            "owner": ds["owner"],
            "visibility": ds["visibility"],
            "derived_from": ds["derived_from"],
            "table_count": len(ds["tables"]),
            "total_rows": sum(t.get("row_count", 0) for t in ds["tables"]),
            "created_at": ds["created_at"],
        })
    return {"datasets": summaries}


@router.get("/{dataset_id}", response_model=Dataset)
def get_dataset(
    dataset_id: str,
    storage: DatasetStorage = Depends(get_dataset_storage),
):
    """Get a dataset by ID."""
    dataset = storage.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.put("/{dataset_id}", response_model=Dataset)
def update_dataset(
    dataset_id: str,
    request: DatasetUpdate,
    storage: DatasetStorage = Depends(get_dataset_storage),
):
    """Update dataset (name, visibility)."""
    dataset = storage.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        return dataset

    updated = storage.update_dataset(dataset_id, **updates)
    return updated


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: str,
    storage: DatasetStorage = Depends(get_dataset_storage),
    database_url: str = Depends(get_database_url),
):
    """Delete a dataset and its PG tables."""
    dataset = storage.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Drop PG tables
    conn = psycopg.connect(database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            for table in dataset["tables"]:
                cur.execute(f'DROP TABLE IF EXISTS "{table["pg_table_name"]}"')
    finally:
        conn.close()

    storage.delete_dataset(dataset_id)
    return None


def _pandas_dtype_to_pg_label(dtype) -> str:
    """Human-readable PG type label."""
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


# --- Promotion Endpoint ---

import re
import uuid


def promote_derived_table_impl(
    session_id: str,
    table_name: str,
    new_name: str,
    dataset_storage: DatasetStorage,
    database_url: str,
) -> dict:
    """
    Promote a derived table to a shareable dataset.

    Copies _derived_{session_id}_{table_name} to _dataset_{new_id}_{table_name}
    and creates a dataset record with lineage tracking.

    Security: Validates table_name contains only alphanumeric and underscores
    to prevent SQL injection.

    Raises:
        HTTPException(400): Invalid table name format
        HTTPException(404): Derived table not found
    """
    # Validate table_name format (alphanumeric + underscores only)
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid table name. Only alphanumeric characters and underscores allowed."
        )

    # Also validate session_id format
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format."
        )

    # Construct derived table name
    derived_table = f"_derived_{session_id}_{table_name}"

    # First verify derived table exists
    conn = psycopg.connect(database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """, (derived_table,))
            exists = cur.fetchone()[0]

            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Derived table '{table_name}' not found in session {session_id}"
                )
    finally:
        conn.close()

    # Create dataset record FIRST to get the ID
    dataset = dataset_storage.create_dataset(
        name=new_name,
        owner="anonymous",  # TODO: Get from auth context
        visibility="private",
    )
    dataset_id = dataset["id"]

    # Now construct the dataset table name using the actual dataset ID
    dataset_table = f"_dataset_{dataset_id}_{table_name}"

    # Copy the table and get metadata
    conn = psycopg.connect(database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            # Copy table structure and data
            cur.execute(f'CREATE TABLE "{dataset_table}" AS SELECT * FROM "{derived_table}"')

            # Get row count
            cur.execute(f'SELECT COUNT(*) FROM "{dataset_table}"')
            row_count = cur.fetchone()[0]

            # Get column info
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (dataset_table,))
            columns_info = cur.fetchall()

    except Exception as e:
        # If table creation fails, delete the dataset record
        dataset_storage.delete_dataset(dataset_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to copy table: {e}"
        )
    finally:
        conn.close()

    # Add table metadata
    dataset_storage.add_table(
        dataset_id=dataset_id,
        name=table_name,
        pg_table_name=dataset_table,
        row_count=row_count,
        columns=[col[0] for col in columns_info],
        dtypes={col[0]: col[1] for col in columns_info},
    )

    # Get updated dataset with tables
    return dataset_storage.get_dataset(dataset_id)


@router.post("/promote", response_model=Dataset)
def promote_derived_table(
    session_id: str = Query(..., description="Session ID containing derived table"),
    table_name: str = Query(..., description="Short name of derived table"),
    new_name: str = Query(..., description="Name for new dataset"),
    storage: DatasetStorage = Depends(get_dataset_storage),
    database_url: str = Depends(get_database_url),
) -> Dataset:
    """
    Promote a derived table to a shareable dataset.

    Copies _derived_{session_id}_{table_name} to _dataset_{new_id}_{table_name}
    and creates a dataset record with lineage tracking.
    """
    result = promote_derived_table_impl(
        session_id=session_id,
        table_name=table_name,
        new_name=new_name,
        dataset_storage=storage,
        database_url=database_url,
    )
    return Dataset(**result)
