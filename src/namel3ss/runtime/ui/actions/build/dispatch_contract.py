from __future__ import annotations

from typing import Callable, Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext

ActionHandler = Callable[[ActionDispatchContext], tuple[dict, Exception | None]]


def merge_action_handlers(groups: Iterable[dict[str, ActionHandler]]) -> dict[str, ActionHandler]:
    merged: dict[str, ActionHandler] = {}
    duplicate_keys: set[str] = set()
    for group in groups:
        for action_type, handler in group.items():
            if action_type in merged:
                duplicate_keys.add(action_type)
                continue
            merged[action_type] = handler
    if duplicate_keys:
        keys_text = ", ".join(sorted(duplicate_keys))
        raise Namel3ssError(f"Duplicate UI action dispatch bindings: {keys_text}")
    return merged


__all__ = ["ActionHandler", "merge_action_handlers"]
