"""MemoryTool - Session-scoped memory for agent insights."""

from datetime import UTC, datetime

from app.storage.file_storage import FileStorage

VALID_CATEGORIES = {"fact", "preference", "correction", "conclusion"}
VALID_ACTIONS = {"add", "remove"}

# Map singular category names to plural storage keys
CATEGORY_TO_KEY = {
    "fact": "facts",
    "preference": "preferences",
    "correction": "corrections",
    "conclusion": "conclusions",
}

EMPTY_MEMORY = {
    "facts": [],
    "preferences": [],
    "corrections": [],
    "conclusions": [],
}


class MemoryTool:
    """
    Update session memory with facts, preferences, corrections, or conclusions.

    The agent calls this tool to explicitly store insights that should persist
    across turns in the session.
    """

    name = "update_memory"

    def __init__(self, storage: FileStorage):
        self._storage = storage

    def execute(
        self,
        tool_input: dict,
        session_id: str,
    ) -> dict:
        """
        Execute a memory update.

        Args:
            tool_input: Dict with action, category, content
            session_id: Session to update

        Returns:
            Dict with success bool and optional error message
        """
        action = tool_input.get("action", "")
        category = tool_input.get("category", "")
        content = tool_input.get("content", "")

        # Validate action
        if action not in VALID_ACTIONS:
            return {
                "success": False,
                "error": f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}",
            }

        # Validate category
        if category not in VALID_CATEGORIES:
            return {
                "success": False,
                "error": f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
            }

        # Validate content
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content cannot be empty",
            }

        # Load session
        session = self._storage.get_session(session_id)
        if session is None:
            return {"success": False, "error": f"Session '{session_id}' not found"}

        # Ensure memory structure exists (backward compat)
        memory = session.get("memory") or _make_empty_memory()

        storage_key = CATEGORY_TO_KEY[category]

        if action == "add":
            entry = {
                "content": content.strip(),
                "added_at": datetime.now(UTC).isoformat(),
            }
            memory[storage_key].append(entry)
        elif action == "remove":
            memory[storage_key] = [
                e for e in memory[storage_key] if e.get("content") != content
            ]

        # Persist
        self._storage.update_session(session_id, {"memory": memory})

        return {"success": True}


def _make_empty_memory() -> dict:
    """Return a fresh empty memory structure."""
    return {
        "facts": [],
        "preferences": [],
        "corrections": [],
        "conclusions": [],
    }
