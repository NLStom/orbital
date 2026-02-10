"""Artifact API endpoints (stub)."""

from fastapi import APIRouter

from app.schemas.artifacts import ArtifactListResponse

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts():
    """List all artifacts. Returns empty list until artifact creation is implemented."""
    return ArtifactListResponse(artifacts=[])
