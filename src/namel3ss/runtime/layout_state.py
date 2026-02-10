from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


class LayoutStateError(RuntimeError):
    """Raised when layout state transitions are invalid."""


_MISSING = object()


def normalize_layout_state(state: Mapping[str, object] | None) -> dict[str, dict]:
    working = dict(state or {})
    drawers = working.get("drawers")
    sticky = working.get("sticky")
    selection = working.get("selection")
    normalized_drawers = dict(drawers) if isinstance(drawers, Mapping) else {}
    normalized_sticky = dict(sticky) if isinstance(sticky, Mapping) else {}
    normalized_selection = dict(selection) if isinstance(selection, Mapping) else {}
    return {
        "drawers": {str(key): bool(value) for key, value in sorted(normalized_drawers.items(), key=lambda item: str(item[0]))},
        "sticky": _normalize_sticky_map(normalized_sticky),
        "selection": {str(key): deepcopy(value) for key, value in sorted(normalized_selection.items(), key=lambda item: str(item[0]))},
    }


def build_layout_state(layout_nodes: Iterable[Mapping[str, object]], *, state: Mapping[str, object] | None = None) -> dict[str, dict]:
    state_root = _state_root(state)
    drawers: dict[str, bool] = {}
    sticky: dict[str, dict[str, object]] = {}
    selection: dict[str, object] = {}
    for node in _iter_layout_nodes(layout_nodes):
        node_type = str(node.get("type") or "")
        node_id = str(node.get("id") or "")
        if node_type == "layout.drawer" and node_id:
            drawers[node_id] = bool(node.get("open_state", False))
        elif node_type == "layout.sticky" and node_id:
            position = "bottom" if node.get("position") == "bottom" else "top"
            sticky[node_id] = {"position": position, "visible": bool(node.get("visible", True))}
        bindings = node.get("bindings")
        if isinstance(bindings, Mapping):
            selected_path = bindings.get("selected_item")
            if isinstance(selected_path, str) and selected_path:
                selection[selected_path] = _read_state_path(state_root, selected_path)
    return normalize_layout_state(
        {
            "drawers": drawers,
            "sticky": sticky,
            "selection": selection,
        }
    )


def apply_layout_action(
    layout_state: Mapping[str, object] | None,
    action: Mapping[str, object],
    *,
    payload: Mapping[str, object] | None = None,
) -> dict[str, dict]:
    state = normalize_layout_state(layout_state)
    action_type = str(action.get("type") or "")
    target = str(action.get("target") or "")
    payload_map = dict(payload or {})

    if action_type == "layout.drawer.open":
        _require_drawer_target(state, target)
        state["drawers"][target] = True
        return state
    if action_type == "layout.drawer.close":
        _require_drawer_target(state, target)
        state["drawers"][target] = False
        return state
    if action_type == "layout.drawer.toggle":
        _require_drawer_target(state, target)
        state["drawers"][target] = not bool(state["drawers"][target])
        return state
    if action_type == "layout.sticky.show":
        _require_sticky_target(state, target)
        state["sticky"][target]["visible"] = True
        return state
    if action_type == "layout.sticky.hide":
        _require_sticky_target(state, target)
        state["sticky"][target]["visible"] = False
        return state
    if action_type == "layout.sticky.toggle":
        _require_sticky_target(state, target)
        state["sticky"][target]["visible"] = not bool(state["sticky"][target].get("visible", True))
        return state
    if action_type == "layout.selection.set":
        path = str(payload_map.get("path") or action.get("path") or "").strip()
        if not path:
            raise LayoutStateError("layout.selection.set requires a state path.")
        state["selection"][path] = deepcopy(payload_map.get("value"))
        return state

    raise LayoutStateError(f"Unsupported layout action type '{action_type}'.")


def apply_layout_actions(
    layout_state: Mapping[str, object] | None,
    actions: Iterable[Mapping[str, object]],
) -> dict[str, dict]:
    state = normalize_layout_state(layout_state)
    sorted_actions = sorted(list(actions), key=_layout_action_sort_key)
    for action in sorted_actions:
        state = apply_layout_action(state, action, payload=None)
    return state


def _layout_action_sort_key(action: Mapping[str, object]) -> tuple[int, int, int, str]:
    order_raw = action.get("order", 0)
    line_raw = action.get("line", 0)
    column_raw = action.get("column", 0)
    order = int(order_raw) if isinstance(order_raw, int) else 0
    line = int(line_raw) if isinstance(line_raw, int) else 0
    column = int(column_raw) if isinstance(column_raw, int) else 0
    action_id = str(action.get("id") or "")
    return (order, line, column, action_id)


def _normalize_sticky_map(values: Mapping[str, object]) -> dict[str, dict[str, object]]:
    normalized: dict[str, dict[str, object]] = {}
    for key, value in sorted(values.items(), key=lambda item: str(item[0])):
        key_text = str(key)
        if not isinstance(value, Mapping):
            normalized[key_text] = {"position": "top", "visible": True}
            continue
        position = "bottom" if value.get("position") == "bottom" else "top"
        normalized[key_text] = {"position": position, "visible": bool(value.get("visible", True))}
    return normalized


def _state_root(state: Mapping[str, object] | None) -> Mapping[str, object]:
    if not isinstance(state, Mapping):
        return {}
    return state


def _read_state_path(state: Mapping[str, object], path: str) -> object | None:
    value = _walk_state_path(state, path)
    if value is not _MISSING:
        return deepcopy(value)
    if path.startswith("ui."):
        value = _walk_state_path(state, path[len("ui.") :])
        if value is not _MISSING:
            return deepcopy(value)
    return None


def _walk_state_path(state: Mapping[str, object], path: str) -> object:
    if not path:
        return _MISSING
    current: object = state
    for segment in path.split("."):
        if not isinstance(current, Mapping):
            return _MISSING
        if segment not in current:
            return _MISSING
        current = current[segment]
    return current


def _iter_layout_nodes(layout_nodes: Iterable[Mapping[str, object]]) -> Iterable[Mapping[str, object]]:
    stack: list[Mapping[str, object]] = [node for node in layout_nodes if isinstance(node, Mapping)]
    while stack:
        node = stack.pop(0)
        yield node
        for key in ("children", "primary", "secondary", "left", "center", "right", "sidebar", "main"):
            child_list = node.get(key)
            if not isinstance(child_list, list):
                continue
            for child in child_list:
                if isinstance(child, Mapping):
                    stack.append(child)


def _require_drawer_target(state: Mapping[str, dict], target: str) -> None:
    if target and target in state["drawers"]:
        return
    raise LayoutStateError(f"Unknown drawer target '{target}'.")


def _require_sticky_target(state: Mapping[str, dict], target: str) -> None:
    if target and target in state["sticky"]:
        return
    raise LayoutStateError(f"Unknown sticky target '{target}'.")


__all__ = [
    "LayoutStateError",
    "apply_layout_action",
    "apply_layout_actions",
    "build_layout_state",
    "normalize_layout_state",
]
