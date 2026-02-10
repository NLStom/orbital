"""
Context management for OrbitalAgent.

Handles:
- Building dynamic system prompts with schema
- Stripping tool details from history
- LLM-powered history summarization
- Summary caching

Separate module for easier debugging and testing.
"""

from typing import Any

from app.schemas.datasets import Dataset


# ============================================================================
# SYSTEM PROMPT BUILDING
# ============================================================================


def build_system_prompt(
    base_prompt: str,
    datasets: list[Dataset],
    derived_tables: list[dict] | None = None,
    memory: dict | None = None,
) -> str:
    """
    Build system prompt with current session state.

    Args:
        base_prompt: Static prompt from system.md
        datasets: List of Dataset objects attached to session
        derived_tables: List of derived table metadata (from DB query)
        memory: Session memory dict with facts/preferences/corrections/conclusions

    Returns:
        Complete system prompt with schema section
    """
    sections = [base_prompt]

    # Add uploaded datasets section
    if datasets:
        sections.append(_format_datasets_section(datasets))

    # Add derived tables section (capped at 10)
    if derived_tables:
        sections.append(_format_derived_section(derived_tables[:10], len(derived_tables)))

    # Add session memory section
    sections.append(_format_memory_section(memory))

    return "\n\n".join(sections)


def _format_datasets_section(datasets: list[Dataset]) -> str:
    """Format uploaded datasets for system prompt."""
    lines = ["## Current Session Data", "", "### Uploaded Datasets", ""]

    for ds in datasets:
        lines.append(f"**{ds.name}**")
        for table in ds.tables:
            # Format columns as "name TYPE"
            cols = ", ".join(
                f"{col} {ds.tables[0].dtypes.get(col, 'UNKNOWN')}"
                for col in table.columns
            ) if table.columns else ""
            lines.append(f"- {table.name} ({table.row_count} rows): {cols}")
        lines.append("")

    return "\n".join(lines)


def _format_memory_section(memory: dict | None) -> str:
    """Format session memory for inclusion in system prompt."""
    lines = ["## Session Memory"]

    if not memory:
        lines.append("")
        lines.append("No memories stored yet. Use `update_memory` to store insights as you discover them.")
        return "\n".join(lines)

    # Check if all categories are empty
    category_map = {
        "facts": "Facts",
        "preferences": "Preferences",
        "corrections": "Corrections",
        "conclusions": "Conclusions",
    }

    has_any = any(memory.get(key, []) for key in category_map)
    if not has_any:
        lines.append("")
        lines.append("No memories stored yet. Use `update_memory` to store insights as you discover them.")
        return "\n".join(lines)

    lines.append("")
    for key, label in category_map.items():
        entries = memory.get(key, [])
        if entries:
            lines.append(f"**{label}:**")
            for entry in entries:
                content = entry.get("content", entry) if isinstance(entry, dict) else entry
                lines.append(f"- {content}")
            lines.append("")

    return "\n".join(lines)


def _format_derived_section(derived: list[dict], total: int) -> str:
    """Format derived tables for system prompt, with cap notice."""
    lines = ["### Derived Tables (created in this session)", ""]

    for t in derived:
        cols = ", ".join(
            f"{c['name']} {c['type']}" for c in t.get("columns", [])
        )
        lines.append(f"- {t['name']} ({t['row_count']} rows): {cols}")

    if total > len(derived):
        lines.append("")
        lines.append(f"*...and {total - len(derived)} more. Use get_schema to see all.*")

    return "\n".join(lines)


# ============================================================================
# HISTORY PREPARATION
# ============================================================================


def prepare_history_for_llm(
    messages: list[dict],
    cached_summary: str | None = None,
    summary_up_to_index: int | None = None,
) -> tuple[list[dict], bool]:
    """
    Prepare message history for LLM, stripping tool details.

    Args:
        messages: Raw message history from storage
        cached_summary: Previously generated summary (if any)
        summary_up_to_index: How many messages the cached summary covers

    Returns:
        (prepared_messages, needs_new_summary)
    """
    MAX_RECENT_TURNS = 3
    TOKEN_THRESHOLD = 6000

    if not messages:
        return [], False

    # Estimate tokens (rough: 1 token ≈ 4 chars)
    history_tokens = sum(len(m.get("content", "") or "") for m in messages) // 4

    # If under threshold, just strip details and return
    if history_tokens <= TOKEN_THRESHOLD or len(messages) <= MAX_RECENT_TURNS * 2:
        return _strip_tool_details(messages), False

    # Split into older (to summarize) and recent (keep full)
    older = messages[:-(MAX_RECENT_TURNS * 2)]
    recent = messages[-(MAX_RECENT_TURNS * 2):]

    # Check if we can use cached summary
    if cached_summary and summary_up_to_index == len(older):
        prepared = [
            {"role": "user", "content": f"[Previous conversation]\n{cached_summary}"},
            *_strip_tool_details(recent),
        ]
        return prepared, False

    # Need new summary - return stripped history and flag
    return _strip_tool_details(messages), True


def _strip_tool_details(messages: list[dict]) -> list[dict]:
    """Strip toolCalls, charts, graphs from messages. Keep text only."""
    prepared = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "") or ""

        if role == "assistant":
            # Keep text only, drop tool artifacts
            prepared.append({
                "role": "assistant",
                "content": content if content else "(performed analysis)",
            })
        elif role == "system":
            # Convert system events to user message with context prefix
            prepared.append({
                "role": "user",
                "content": f"[Context] {content}",
            })
        else:
            prepared.append({"role": role, "content": content})

    return prepared


# ============================================================================
# LLM SUMMARIZATION
# ============================================================================


SUMMARIZE_PROMPT = """Summarize this conversation history for an AI data analysis agent.
Focus on:
- What data the user is working with
- Key questions asked and insights discovered
- Charts/graphs created and what they showed
- Any user preferences or corrections mentioned

Keep it under 200 words. Be factual and concise.

Conversation:
{conversation}"""


async def summarize_history(
    messages: list[dict],
    llm_provider: Any,
) -> str:
    """
    Use LLM to summarize older conversation history.

    Args:
        messages: Messages to summarize (older portion)
        llm_provider: LLM provider instance for API call

    Returns:
        Summary string (~200 words)
    """
    # Format messages for summarization
    conversation_text = _format_for_summary(messages)

    # Call LLM
    response = await llm_provider.generate(
        messages=[{
            "role": "user",
            "content": SUMMARIZE_PROMPT.format(conversation=conversation_text),
        }],
        max_tokens=500,
    )

    return response.content


def _format_for_summary(messages: list[dict]) -> str:
    """Format messages into readable text for summarization."""
    lines = []

    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "") or ""
        # Truncate long messages to 500 chars
        if len(content) > 500:
            content = content[:500]
        lines.append(f"{role}: {content}")

    return "\n\n".join(lines)
