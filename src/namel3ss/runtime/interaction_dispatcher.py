from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from namel3ss.runtime.layout_state import apply_layout_action, normalize_layout_state


class InteractionDispatcherError(RuntimeError):
    """Raised when interaction dispatch cannot be completed."""


_LAYOUT_STATE_ACTION_TYPES = {
    "layout.drawer.open",
    "layout.drawer.close",
    "layout.drawer.toggle",
    "layout.sticky.show",
    "layout.sticky.hide",
    "layout.sticky.toggle",
    "layout.selection.set",
}


@dataclass(frozen=True)
class InteractionEvent:
    action_id: str
    payload: Mapping[str, object] | None = None
    order: int = 0
    line: int | None = None
    column: int | None = None


def normalize_action_registry(actions: Mapping[str, object] | Iterable[Mapping[str, object]]) -> dict[str, dict]:
    registry: dict[str, dict] = {}
    if isinstance(actions, Mapping):
        for action_id, raw in sorted(actions.items(), key=lambda item: str(item[0])):
            if isinstance(raw, Mapping):
                entry = dict(raw)
                entry.setdefault("id", str(action_id))
                registry[str(action_id)] = entry
        return registry
    for raw in actions:
        if not isinstance(raw, Mapping):
            continue
        action_id = str(raw.get("id") or "")
        if not action_id:
            continue
        registry[action_id] = dict(raw)
    return {action_id: registry[action_id] for action_id in sorted(registry)}


def keyboard_action_ids(actions: Mapping[str, object] | Iterable[Mapping[str, object]], shortcut: str) -> list[str]:
    registry = normalize_action_registry(actions)
    target_combo = _normalize_shortcut(shortcut)
    matches: list[tuple[int, int, int, str]] = []
    for action_id, action in registry.items():
        action_type = str(action.get("type") or "")
        if action_type != "layout.shortcut":
            continue
        combo = _normalize_shortcut(str(action.get("shortcut") or action.get("target") or ""))
        if combo != target_combo:
            continue
        order, line, column = _action_priority(action)
        matches.append((order, line, column, action_id))
    matches.sort()
    return [action_id for _order, _line, _column, action_id in matches]


def dispatch_interactions(
    layout_state: Mapping[str, object] | None,
    *,
    actions: Mapping[str, object] | Iterable[Mapping[str, object]],
    events: Iterable[InteractionEvent | Mapping[str, object]],
    executor: Callable[[dict, Mapping[str, object] | None], object] | None = None,
) -> dict[str, object]:
    registry = normalize_action_registry(actions)
    queued = sorted((_normalize_event(event) for event in events), key=_event_sort_key)
    state = normalize_layout_state(layout_state)
    executed: list[str] = []
    results: list[dict[str, object]] = []

    for event in queued:
        action = registry.get(event.action_id)
        if action is None:
            raise InteractionDispatcherError(f"Unknown action id '{event.action_id}'.")
        action_type = str(action.get("type") or "")
        payload = event.payload
        if action_type in _LAYOUT_STATE_ACTION_TYPES:
            state = apply_layout_action(state, action, payload=payload)
            results.append({"action_id": event.action_id, "status": "applied"})
        elif executor is not None:
            result = executor(action, payload)
            results.append({"action_id": event.action_id, "status": "delegated", "result": result})
        else:
            results.append({"action_id": event.action_id, "status": "queued"})
        executed.append(event.action_id)
    return {
        "state": state,
        "executed": executed,
        "results": results,
    }


def _normalize_event(event: InteractionEvent | Mapping[str, object]) -> InteractionEvent:
    if isinstance(event, InteractionEvent):
        return event
    if not isinstance(event, Mapping):
        raise InteractionDispatcherError("Interaction events must be mappings or InteractionEvent instances.")
    action_id = str(event.get("action_id") or "")
    if not action_id:
        raise InteractionDispatcherError("Interaction events require action_id.")
    payload_raw = event.get("payload")
    payload = payload_raw if isinstance(payload_raw, Mapping) else None
    order_raw = event.get("order", 0)
    line_raw = event.get("line")
    column_raw = event.get("column")
    order = int(order_raw) if isinstance(order_raw, int) else 0
    line = int(line_raw) if isinstance(line_raw, int) else None
    column = int(column_raw) if isinstance(column_raw, int) else None
    return InteractionEvent(
        action_id=action_id,
        payload=payload,
        order=order,
        line=line,
        column=column,
    )


def _event_sort_key(event: InteractionEvent) -> tuple[int, int, int, str]:
    return (
        event.order,
        event.line or 0,
        event.column or 0,
        event.action_id,
    )


def _action_priority(action: Mapping[str, object]) -> tuple[int, int, int]:
    order_raw = action.get("order", 0)
    line_raw = action.get("line", 0)
    column_raw = action.get("column", 0)
    order = int(order_raw) if isinstance(order_raw, int) else 0
    line = int(line_raw) if isinstance(line_raw, int) else 0
    column = int(column_raw) if isinstance(column_raw, int) else 0
    return order, line, column


def _normalize_shortcut(value: str) -> str:
    parts = [segment.strip().lower() for segment in value.split("+") if segment.strip()]
    modifiers = sorted(part for part in parts if part in {"ctrl", "shift", "alt", "meta"})
    keys = [part for part in parts if part not in {"ctrl", "shift", "alt", "meta"}]
    if not keys:
        return "+".join(modifiers)
    return "+".join(modifiers + keys)


__all__ = [
    "InteractionDispatcherError",
    "InteractionEvent",
    "dispatch_interactions",
    "keyboard_action_ids",
    "normalize_action_registry",
]
