"""
Config router - runtime API key configuration.

Allows judges/users to provide their own Google API key at runtime
without requiring server-side environment variables.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["config"])

# In-memory runtime config (survives until server restart)
_runtime_config: dict = {}


class ConfigRequest(BaseModel):
    google_api_key: str


@router.post("/config")
def set_config(body: ConfigRequest):
    """Store a runtime Google API key and reset cached providers."""
    _runtime_config["google_api_key"] = body.google_api_key
    # Lazy import to avoid circular dependency (dependencies -> factory -> config)
    from app.dependencies import reset_agent
    reset_agent()
    return {"ok": True}


@router.get("/config/status")
def get_config_status():
    """Return whether a Google API key is configured (never exposes the actual key)."""
    return {"google_api_key_set": bool(_runtime_config.get("google_api_key"))}


def get_runtime_api_key() -> str | None:
    """Return the runtime-provided Google API key, if any."""
    return _runtime_config.get("google_api_key") or None
