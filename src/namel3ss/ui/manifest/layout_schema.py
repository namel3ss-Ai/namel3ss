from __future__ import annotations

import json
from typing import Any, Mapping

from namel3ss.ir.ui import layout_ir as ir


def _empty_bindings() -> dict[str, Any]:
    return {
        "on_click": None,
        "keyboard_shortcut": None,
        "selected_item": None,
    }


def _clone_default(value: Any) -> Any:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


LAYOUT_NODE_SCHEMA: dict[str, tuple[str, ...]] = {
    "layout.sidebar": ("id", "children", "bindings"),
    "layout.main": ("id", "children", "bindings"),
    "layout.drawer": ("id", "side", "trigger_id", "children", "bindings"),
    "layout.sticky": ("id", "position", "children", "bindings"),
    "layout.scroll_area": ("id", "axis", "children", "bindings"),
    "layout.two_pane": ("id", "primary", "secondary", "bindings"),
    "layout.three_pane": ("id", "left", "center", "right", "bindings"),
    "component.form": ("id", "name", "wizard", "sections", "children", "bindings"),
    "component.table": (
        "id",
        "name",
        "reorderable_columns",
        "fixed_header",
        "children",
        "bindings",
    ),
    "component.card": ("id", "name", "expandable", "collapsed", "children", "bindings"),
    "component.tabs": ("id", "name", "dynamic_from_state", "children", "bindings"),
    "component.media": ("id", "name", "inline_crop", "annotation", "children", "bindings"),
    "component.literal": ("id", "text", "bindings"),
}

NODE_FIELD_DEFAULTS: dict[str, dict[str, Any]] = {
    "layout.sidebar": {"children": [], "bindings": _empty_bindings()},
    "layout.main": {"children": [], "bindings": _empty_bindings()},
    "layout.drawer": {"side": "right", "trigger_id": "", "children": [], "bindings": _empty_bindings()},
    "layout.sticky": {"position": "bottom", "children": [], "bindings": _empty_bindings()},
    "layout.scroll_area": {"axis": "vertical", "children": [], "bindings": _empty_bindings()},
    "layout.two_pane": {"primary": [], "secondary": [], "bindings": _empty_bindings()},
    "layout.three_pane": {"left": [], "center": [], "right": [], "bindings": _empty_bindings()},
    "component.form": {"wizard": False, "sections": [], "children": [], "bindings": _empty_bindings()},
    "component.table": {"reorderable_columns": False, "fixed_header": False, "children": [], "bindings": _empty_bindings()},
    "component.card": {"expandable": False, "collapsed": False, "children": [], "bindings": _empty_bindings()},
    "component.tabs": {"dynamic_from_state": None, "children": [], "bindings": _empty_bindings()},
    "component.media": {"inline_crop": False, "annotation": False, "children": [], "bindings": _empty_bindings()},
    "component.literal": {"text": "", "bindings": _empty_bindings()},
}


def build_layout_manifest(page: ir.PageLayoutIR) -> dict[str, Any]:
    layout_nodes = [_node_to_manifest(node) for node in page.elements]
    actions = [
        {
            "id": action.id,
            "event": action.event,
            "node_id": action.node_id,
            "target": action.target,
            "line": action.line,
            "column": action.column,
        }
        for action in page.actions
    ]
    state = [{"path": path, "default": None} for path in page.state_paths]
    manifest = {
        "manifest_version": "1.0",
        "capabilities": ["ui.custom_layouts"],
        "page": {"name": page.name},
        "state": state,
        "layout": layout_nodes,
        "actions": actions,
    }
    validate_layout_manifest(manifest)
    return manifest


def normalize_layout_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(manifest)
    normalized.setdefault("manifest_version", "1.0")
    normalized.setdefault("capabilities", [])
    normalized.setdefault("page", {"name": ""})
    normalized.setdefault("state", [])
    normalized.setdefault("layout", [])
    normalized.setdefault("actions", [])

    normalized_state = []
    for entry in normalized.get("state", []):
        if not isinstance(entry, Mapping):
            continue
        normalized_state.append(
            {
                "path": str(entry.get("path") or ""),
                "default": entry.get("default", None),
            }
        )
    normalized["state"] = normalized_state

    normalized_layout = []
    for raw in normalized.get("layout", []):
        if not isinstance(raw, Mapping):
            continue
        normalized_layout.append(_normalize_node(raw))
    normalized["layout"] = normalized_layout

    normalized_actions = []
    for action in normalized.get("actions", []):
        if not isinstance(action, Mapping):
            continue
        normalized_actions.append(
            {
                "id": str(action.get("id") or ""),
                "event": str(action.get("event") or ""),
                "node_id": str(action.get("node_id") or ""),
                "target": str(action.get("target") or ""),
                "line": action.get("line"),
                "column": action.get("column"),
            }
        )
    normalized["actions"] = normalized_actions
    return normalized


def validate_layout_manifest(manifest: Mapping[str, Any]) -> None:
    if not isinstance(manifest, Mapping):
        raise ValueError("Manifest must be a mapping.")
    if not isinstance(manifest.get("layout"), list):
        raise ValueError("Manifest layout must be a list.")
    if not isinstance(manifest.get("actions"), list):
        raise ValueError("Manifest actions must be a list.")
    for node in manifest["layout"]:
        _validate_node(node)
    for action in manifest["actions"]:
        if not isinstance(action, Mapping):
            raise ValueError("Action entries must be objects.")
        for field in ("id", "event", "node_id", "target"):
            if field not in action or action[field] in {"", None}:
                raise ValueError(f'Action is missing required field "{field}".')


def manifest_json(manifest: Mapping[str, Any], *, pretty: bool = True) -> str:
    payload = normalize_layout_manifest(manifest)
    if pretty:
        return json.dumps(payload, indent=2, ensure_ascii=True)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _node_to_manifest(node: ir.LayoutElementIR) -> dict[str, Any]:
    if isinstance(node, ir.SidebarIR):
        return _with_common(
            node,
            {"type": "layout.sidebar", "children": [_node_to_manifest(child) for child in node.children]},
        )
    if isinstance(node, ir.MainIR):
        return _with_common(
            node,
            {"type": "layout.main", "children": [_node_to_manifest(child) for child in node.children]},
        )
    if isinstance(node, ir.DrawerIR):
        return _with_common(
            node,
            {
                "type": "layout.drawer",
                "side": node.side,
                "trigger_id": node.trigger_id,
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.StickyIR):
        return _with_common(
            node,
            {
                "type": "layout.sticky",
                "position": node.position,
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.ScrollAreaIR):
        return _with_common(
            node,
            {
                "type": "layout.scroll_area",
                "axis": node.axis,
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.TwoPaneIR):
        return _with_common(
            node,
            {
                "type": "layout.two_pane",
                "primary": [_node_to_manifest(child) for child in node.primary],
                "secondary": [_node_to_manifest(child) for child in node.secondary],
            },
        )
    if isinstance(node, ir.ThreePaneIR):
        return _with_common(
            node,
            {
                "type": "layout.three_pane",
                "left": [_node_to_manifest(child) for child in node.left],
                "center": [_node_to_manifest(child) for child in node.center],
                "right": [_node_to_manifest(child) for child in node.right],
            },
        )
    if isinstance(node, ir.FormIR):
        return _with_common(
            node,
            {
                "type": "component.form",
                "name": node.name,
                "wizard": bool(node.wizard),
                "sections": list(node.sections),
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.TableIR):
        return _with_common(
            node,
            {
                "type": "component.table",
                "name": node.name,
                "reorderable_columns": bool(node.reorderable_columns),
                "fixed_header": bool(node.fixed_header),
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.CardIR):
        return _with_common(
            node,
            {
                "type": "component.card",
                "name": node.name,
                "expandable": bool(node.expandable),
                "collapsed": bool(node.collapsed),
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.NavigationTabsIR):
        return _with_common(
            node,
            {
                "type": "component.tabs",
                "name": node.name,
                "dynamic_from_state": node.dynamic_from_state,
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.MediaIR):
        return _with_common(
            node,
            {
                "type": "component.media",
                "name": node.name,
                "inline_crop": bool(node.inline_crop),
                "annotation": bool(node.annotation),
                "children": [_node_to_manifest(child) for child in node.children],
            },
        )
    if isinstance(node, ir.LiteralItemIR):
        return _with_common(node, {"type": "component.literal", "text": node.text})
    raise TypeError(f"Unsupported IR node type: {type(node)!r}")


def _with_common(node: Any, payload: dict[str, Any]) -> dict[str, Any]:
    payload["id"] = node.id
    payload["bindings"] = {
        "on_click": node.bindings.on_click,
        "keyboard_shortcut": node.bindings.keyboard_shortcut,
        "selected_item": node.bindings.selected_item,
    }
    payload["line"] = node.line
    payload["column"] = node.column
    return payload


def _normalize_node(node: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(node.get("type") or "")
    normalized = dict(node)
    defaults = NODE_FIELD_DEFAULTS.get(kind, {})
    for key, value in defaults.items():
        normalized.setdefault(key, _clone_default(value))
    if "bindings" not in normalized or not isinstance(normalized["bindings"], Mapping):
        normalized["bindings"] = _empty_bindings()
    else:
        bindings = normalized["bindings"]
        normalized["bindings"] = {
            "on_click": bindings.get("on_click"),
            "keyboard_shortcut": bindings.get("keyboard_shortcut"),
            "selected_item": bindings.get("selected_item"),
        }

    for child_key in ("children", "primary", "secondary", "left", "center", "right"):
        raw_children = normalized.get(child_key)
        if not isinstance(raw_children, list):
            continue
        normalized[child_key] = [_normalize_node(entry) for entry in raw_children if isinstance(entry, Mapping)]
    return normalized


def _validate_node(node: Any) -> None:
    if not isinstance(node, Mapping):
        raise ValueError("Layout node entries must be objects.")
    kind = str(node.get("type") or "")
    required = LAYOUT_NODE_SCHEMA.get(kind)
    if required is None:
        return
    for key in required:
        if key not in node:
            raise ValueError(f'Layout node "{kind}" is missing required field "{key}".')


__all__ = [
    "LAYOUT_NODE_SCHEMA",
    "NODE_FIELD_DEFAULTS",
    "build_layout_manifest",
    "manifest_json",
    "normalize_layout_manifest",
    "validate_layout_manifest",
]
