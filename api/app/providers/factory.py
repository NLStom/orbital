"""
Provider factory for creating LLM providers.

Creates the appropriate provider based on model selection and configuration.
"""

from enum import Enum

from pydantic import BaseModel

from app.config import Settings
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.vertex_ai import VertexAIProvider


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    GEMINI = "gemini"  # Google AI Studio
    VERTEX_AI = "vertex_ai"  # Google Cloud Vertex AI


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    provider: LLMProviderType
    model_id: str
    display_name: str
    max_tokens: int = 8192
    context_window: int = 200_000
    supports_tools: bool = True


# Available models registry
AVAILABLE_MODELS: dict[str, ModelConfig] = {
    "vertex-gemini-3-pro": ModelConfig(
        provider=LLMProviderType.VERTEX_AI,
        model_id="gemini-3-pro-preview",
        display_name="Gemini 3 Pro",
        max_tokens=65536,
        context_window=1_048_576,
    ),
}


class ProviderFactory:
    """Factory to create LLM providers based on configuration."""

    def __init__(self, settings: Settings):
        """
        Initialize factory with settings.

        Args:
            settings: Application settings with API keys
        """
        self.settings = settings

    def create(self, model_key: str) -> LLMProvider:
        """
        Create a provider for the specified model.

        Args:
            model_key: Model key from AVAILABLE_MODELS

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If model unknown or API key not configured
        """
        if model_key not in AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_key}")

        config = AVAILABLE_MODELS[model_key]

        match config.provider:
            case LLMProviderType.GEMINI:
                if not self.settings.gemini_api_key:
                    raise ValueError("GEMINI_API_KEY not configured")
                return GeminiProvider(
                    api_key=self.settings.gemini_api_key,
                    model_id=config.model_id,
                )

            case LLMProviderType.VERTEX_AI:
                if not self.settings.google_api_key:
                    raise ValueError("GOOGLE_API_KEY not configured for Vertex AI")
                return VertexAIProvider(
                    api_key=self.settings.google_api_key,
                    model_id=config.model_id,
                )

    def has_api_key(self, model_key: str) -> bool:
        """Return True if the model has a configured API key."""
        config = AVAILABLE_MODELS.get(model_key)
        if not config:
            return False

        match config.provider:
            case LLMProviderType.GEMINI:
                return bool(self.settings.gemini_api_key)
            case LLMProviderType.VERTEX_AI:
                return bool(self.settings.google_api_key)

        return False

    def get_available_models(self) -> list[dict]:
        """
        Return list of models that have API keys configured.

        Returns:
            List of model dicts with key, display_name, provider
        """
        available = []
        for key, config in AVAILABLE_MODELS.items():
            has_key = False
            match config.provider:
                case LLMProviderType.GEMINI:
                    has_key = bool(self.settings.gemini_api_key)
                case LLMProviderType.VERTEX_AI:
                    has_key = bool(self.settings.google_api_key)

            if has_key:
                available.append(
                    {
                        "key": key,
                        "display_name": config.display_name,
                        "provider": config.provider.value,
                    }
                )
        return available
