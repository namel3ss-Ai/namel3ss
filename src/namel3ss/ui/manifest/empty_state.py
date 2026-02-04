from __future__ import annotations

# Default empty-state content for list/table when app does not specify empty_text.
# Keeps manifest deterministic and ensures empty collections render an empty state.
_DEFAULT_EMPTY_STATE_LIST = {"title": "No items", "text": "There are no items to display."}
_DEFAULT_EMPTY_STATE_TABLE = {"title": "No rows", "text": "There are no rows to display."}


def _empty_state_for_list(empty_text: str | None) -> dict:
    """Return deterministic empty_state dict for a list element."""
    if empty_text:
        return {"title": "No items", "text": empty_text}
    return dict(_DEFAULT_EMPTY_STATE_LIST)


def _empty_state_for_table(empty_text: str | None) -> dict:
    """Return deterministic empty_state dict for a table element."""
    if empty_text:
        return {"title": "No rows", "text": empty_text}
    return dict(_DEFAULT_EMPTY_STATE_TABLE)


__all__ = ["_empty_state_for_list", "_empty_state_for_table"]
