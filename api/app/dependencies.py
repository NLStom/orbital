"""
FastAPI dependencies for dependency injection.
"""

from functools import lru_cache

import anthropic

from app.agent import OrbitalAgent
from app.config import get_settings
from app.data.loader import DataLoader
from app.providers.factory import AVAILABLE_MODELS, ProviderFactory
from app.storage.dataset_storage import DatasetStorage
from app.storage.file_storage import FileStorage


@lru_cache
def get_storage() -> FileStorage:
    """Get FileStorage singleton for dependency injection."""
    return FileStorage()


# Dataset storage singleton
_dataset_storage: DatasetStorage | None = None


def get_dataset_storage() -> DatasetStorage:
    """Get DatasetStorage singleton."""
    global _dataset_storage
    if _dataset_storage is None:
        settings = get_settings()
        _dataset_storage = DatasetStorage(database_url=settings.database_url)
        _dataset_storage.initialize()
    return _dataset_storage


# Cache agents per (source_id, model) for conversation persistence
_agents: dict[tuple[str, str], OrbitalAgent] = {}

# Provider factory instance
_factory: ProviderFactory | None = None


def get_provider_factory() -> ProviderFactory:
    """Get or create ProviderFactory instance."""
    global _factory
    if _factory is None:
        settings = get_settings()
        _factory = ProviderFactory(settings)
    return _factory


def get_anthropic_client() -> anthropic.Anthropic:
    """Get Anthropic client instance."""
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_agent_for_source(
    source_id: str,
    model: str | None = None,
    dataset_ids: list[str] | None = None,
    session_id: str | None = None,
) -> tuple[OrbitalAgent, str]:
    """
    Get a OrbitalAgent for a specific data source and model.

    Caches agents per (source, model) when no dataset_ids are provided.
    When dataset_ids are given, creates a fresh agent with dataset-aware DataLoader.

    Args:
        source_id: The data source identifier
        model: Optional model key (defaults to settings.default_model)
        dataset_ids: Optional dataset IDs to make visible to the agent

    Returns:
        Tuple of (OrbitalAgent, model_key) configured for the specified data source

    Raises:
        ValueError: If model unknown or API key not configured
    """
    global _agents
    settings = get_settings()

    factory = get_provider_factory()

    # Use default model if not specified and validate it exists
    model_key = model or settings.default_model
    if model_key not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model: {model_key}")

    # Fall back to the first configured model if the default lacks credentials
    if model is None and not factory.has_api_key(model_key):
        available = factory.get_available_models()
        if not available:
            raise ValueError(
                "No LLM API keys configured. Set ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY."
            )
        model_key = available[0]["key"]

    # Get dataset storage and database URL for Phase 2 tools
    dataset_storage = get_dataset_storage()
    database_url = settings.database_url

    file_storage = get_storage()

    # When datasets are attached, create a fresh agent with dataset awareness
    if dataset_ids:
        provider = factory.create(model_key)
        data_loader = DataLoader(dataset_ids=dataset_ids, session_id=session_id)
        agent = OrbitalAgent(
            provider=provider,
            data_loader=data_loader,
            dataset_storage=dataset_storage,
            database_url=database_url,
            storage=file_storage,
        )
        return agent, model_key

    cache_key = (source_id, model_key)
    if cache_key not in _agents:
        provider = factory.create(model_key)
        data_loader = DataLoader()
        _agents[cache_key] = OrbitalAgent(
            provider=provider,
            data_loader=data_loader,
            dataset_storage=dataset_storage,
            database_url=database_url,
            storage=file_storage,
        )

    return _agents[cache_key], model_key


def get_agent() -> OrbitalAgent:
    """
    Get the default OrbitalAgent (custom).

    For backwards compatibility.
    """
    agent, _ = get_agent_for_source("custom")
    return agent


def reset_agent() -> None:
    """Reset all agent instances (useful for testing)."""
    global _agents, _factory, _dataset_storage
    _agents = {}
    _factory = None
    _dataset_storage = None
