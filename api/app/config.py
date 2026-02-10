"""
Configuration settings for Orbital API.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve config directory (api/app) and candidate .env locations
_APP_DIR = Path(__file__).parent.parent
_ENV_FILES = (
    # API-specific .env (legacy location inside orbital/api)
    _APP_DIR / ".env",
    # Repository root .env (preferred for dev secrets shared across apps)
    _APP_DIR.parent.parent / ".env",
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
    )

    # API Keys (at least one required for the app to work)
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    google_genai_use_vertexai: bool | None = None  # allows env flag without validation errors
    openai_api_key: str = ""

    # Model settings
    default_model: str = "vertex-gemini-3-pro"
    max_tokens: int = 4096
    system_prompt_name: str = "system"

    # Database
    database_url: str = "postgresql://localhost/orbital"

    # Session creator display name (defaults to system $USER in FileStorage)
    orbital_user: str = ""

    # Legacy (kept for backwards compatibility)
    model_name: str = "claude-sonnet-4-20250514"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
