"""
Session API endpoints.

CRUD operations for sessions (chat history with insights).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import get_storage, get_provider_factory
from app.schemas.sessions import (
    Session,
    SessionCreate,
    SessionListResponse,
    SessionUpdate,
)
from app.services.schema_generator import SchemaGenerator
from app.storage.pg_session_storage import PgSessionStorage
from app.storage.dataset_storage import DatasetStorage
from app.routers.datasets import get_dataset_storage, get_database_url
from app.providers.factory import ProviderFactory
from app.config import get_settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


VALID_DATA_SOURCES = {"custom"}


class GenerateTitleResponse(BaseModel):
    """Response for generate-title endpoint."""
    title: str = Field(..., max_length=100)


@router.get("", response_model=SessionListResponse)
def list_sessions(storage: PgSessionStorage = Depends(get_storage)):
    """List all sessions, sorted by updatedAt descending."""
    sessions = storage.list_sessions()
    return {"sessions": sessions}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Session)
def create_session(
    request: SessionCreate,
    storage: PgSessionStorage = Depends(get_storage),
    dataset_storage: DatasetStorage = Depends(get_dataset_storage),
):
    """Create a new session, optionally with datasets attached."""
    # Deduplicate and validate dataset_ids BEFORE creating session
    dataset_ids = []
    if request.dataset_ids:
        # Deduplicate while preserving order
        seen = set()
        for ds_id in request.dataset_ids:
            if ds_id not in seen:
                seen.add(ds_id)
                dataset_ids.append(ds_id)

        # Validate ALL datasets exist before creating session
        for ds_id in dataset_ids:
            dataset = dataset_storage.get_dataset(ds_id)
            if dataset is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dataset {ds_id} not found"
                )

    # Create session
    session = storage.create_session(
        data_source=request.dataSource,
        name=request.name or ""
    )

    # Attach datasets if provided
    try:
        for ds_id in dataset_ids:
            session = storage.update_session(
                session_id=session["id"],
                updates={"addDataset": ds_id}
            )
    except Exception as e:
        # Rollback: delete the session if dataset attachment fails
        storage.delete_session(session["id"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach datasets: {e}"
        )

    return session


@router.get("/{session_id}", response_model=Session)
def get_session(
    session_id: str, storage: PgSessionStorage = Depends(get_storage)
):
    """Get a session by ID with messages and insights."""
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}", response_model=Session)
def update_session(
    session_id: str, request: SessionUpdate, storage: PgSessionStorage = Depends(get_storage)
):
    """Update a session (name, addMessage, addInsight, updateInsight)."""
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.addMessage is not None:
        updates["addMessage"] = request.addMessage.model_dump(exclude_none=True)
    if request.addInsight is not None:
        updates["addInsight"] = request.addInsight.model_dump(exclude_none=True)
    if request.updateInsight is not None:
        updates["updateInsight"] = request.updateInsight.model_dump(exclude_none=True)

    updated = storage.update_session(session_id, updates)
    return updated


@router.post("/{session_id}/generate-title", response_model=GenerateTitleResponse)
async def generate_session_title(
    session_id: str,
    storage: PgSessionStorage = Depends(get_storage),
    dataset_storage: DatasetStorage = Depends(get_dataset_storage),
    provider_factory: ProviderFactory = Depends(get_provider_factory),
):
    """Generate a descriptive title for a session using LLM."""
    import logging
    logger = logging.getLogger(__name__)

    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    print(f"[TITLE GEN] Session: {session_id}", flush=True)

    # Build context from session data
    context_parts = []

    # Add data source
    context_parts.append(f"Data source: {session['dataSource']}")

    # Add dataset names (if any)
    dataset_ids = session.get("datasets", [])
    if dataset_ids:
        dataset_names = []
        for ds_id in dataset_ids[:3]:  # Limit to 3
            ds = dataset_storage.get_dataset(ds_id)
            if ds:
                dataset_names.append(ds.get("name", ds_id))
        if dataset_names:
            context_parts.append(f"Datasets: {', '.join(dataset_names)}")

    # Collect conversation content
    messages = session.get("messages", [])

    # Get chart/graph titles (these are very descriptive)
    viz_titles = []
    for msg in messages:
        if msg.get("role") == "assistant":
            for chart in msg.get("charts", []):
                if chart.get("title"):
                    viz_titles.append(chart["title"])
            for graph in msg.get("graphs", []):
                if graph.get("title"):
                    viz_titles.append(graph["title"])

    if viz_titles:
        context_parts.append(f"Visualizations created: {', '.join(viz_titles[:5])}")

    # Get first few user questions
    user_messages = [m["content"][:150] for m in messages if m.get("role") == "user"][:3]
    if user_messages:
        context_parts.append("User questions:")
        for q in user_messages:
            context_parts.append(f"- {q}")

    # Get key content from assistant responses (first paragraph of each)
    assistant_snippets = []
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("content"):
            # Get first 200 chars of response
            snippet = msg["content"][:200].split("\n")[0]
            if snippet and len(snippet) > 20:
                assistant_snippets.append(snippet)

    if assistant_snippets:
        context_parts.append("Analysis snippets:")
        for snippet in assistant_snippets[:3]:
            context_parts.append(f"- {snippet}")

    context = "\n".join(context_parts)

    print(f"[TITLE GEN] Context:\n{context}", flush=True)

    # LLM prompt
    prompt = f"""Generate a concise, specific title for this data analysis session.

Session context:
{context}

Instructions:
- Create a title that captures WHAT is being analyzed (e.g., "Apple Sales Forecast 2025", "VNDB Game Ratings Analysis")
- Maximum 50 characters
- Be specific - mention the subject matter, not generic terms
- Title case, no quotes
- Focus on the main topic from visualizations and questions

Return ONLY the title text, nothing else."""

    # Call LLM using provider_factory (Gemini 3 Pro via Vertex AI)
    try:
        provider = provider_factory.create("vertex-gemini-3-pro")
        response = await provider.generate(
            messages=[{"role": "user", "content": prompt}],
        )

        print(f"[TITLE GEN] LLM response: {response.content}", flush=True)

        if not response.content:
            raise HTTPException(status_code=500, detail="LLM returned empty response")

        title = response.content.strip()[:100]
        return {"title": title}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[TITLE GEN] Error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Title generation failed: {str(e)}")


@router.get("/{session_id}/schema")
def get_session_schema(
    session_id: str, storage: PgSessionStorage = Depends(get_storage)
):
    """
    Get ER diagram schema scoped to a session's data source and datasets.

    Resolves the session's dataSource and dataset_ids internally.
    When datasets are attached, only their tables are included.
    """
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    source_id = session["dataSource"]
    dataset_ids = session.get("datasets") or None
    # Treat empty list as None (show all tables)
    if dataset_ids is not None and len(dataset_ids) == 0:
        dataset_ids = None

    try:
        generator = SchemaGenerator()
        schema = generator.generate(source_id, dataset_ids=dataset_ids)
        return schema
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate schema") from e


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    storage: PgSessionStorage = Depends(get_storage),
    database_url: str = Depends(get_database_url),
):
    """Delete a session and clean up derived tables."""
    import logging
    import psycopg

    logger = logging.getLogger(__name__)

    # Get session to check if it exists
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up derived tables for this session
    try:
        conn = psycopg.connect(database_url, autocommit=True)
        try:
            with conn.cursor() as cur:
                # Find all derived tables for this session
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name LIKE %s
                """, (f"_derived_{session_id}_%",))
                derived_tables = [row[0] for row in cur.fetchall()]

                # Drop each derived table
                for table_name in derived_tables:
                    try:
                        cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                        logger.info(f"Dropped derived table: {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to drop table {table_name}: {e}")
        finally:
            conn.close()
    except Exception as e:
        # Log error but don't fail deletion
        logger.warning(f"Failed to clean up derived tables for session {session_id}: {e}")

    # Delete session file
    deleted = storage.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


@router.delete("", response_model=dict)
def delete_empty_sessions(storage: PgSessionStorage = Depends(get_storage)):
    """Delete all sessions with zero messages and zero datasets."""
    deleted_count = storage.delete_empty_sessions()
    return {"deleted": deleted_count}
