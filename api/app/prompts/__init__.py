"""
Prompt management for Orbital agent.

Loads LLM-facing prompts from .md files at import time and caches them
in memory. Developers can edit the .md files directly without touching Python.
"""

import os
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


class PromptRegistry:
    """In-memory cache of prompt files loaded from the prompts/ directory."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, name: str) -> str:
        """
        Return the prompt text for *name*.

        Looks for ``prompts/{name}.md`` on first access and caches the result.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
        """
        if name not in self._cache:
            path = _PROMPTS_DIR / f"{name}.md"
            self._cache[name] = path.read_text(encoding="utf-8").strip()
        return self._cache[name]

    def reload(self, name: str | None = None) -> None:
        """Clear cache for *name* (or all prompts) so the next ``get()`` re-reads disk."""
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(name, None)


# Module-level singleton — imported by agent code.
registry = PromptRegistry()


def load_prompt(name: str) -> str:
    """Convenience wrapper: ``load_prompt("system")`` → contents of ``system.md``."""
    return registry.get(name)
