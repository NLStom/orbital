"""
Models router - lists available LLM models.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.providers.factory import ProviderFactory

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
def list_models():
    """
    List all available models.

    Returns only models that have API keys configured.
    Also returns the default model.
    """
    settings = get_settings()
    factory = ProviderFactory(settings)

    return {
        "models": factory.get_available_models(),
        "default": settings.default_model,
    }
