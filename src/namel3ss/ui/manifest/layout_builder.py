from __future__ import annotations

from typing import Iterable, Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.ui import layout_ir as ir
from namel3ss.runtime.layout_state import build_layout_state
from namel3ss.ui.manifest.actions import build_layout_action_entry, normalize_action_entry
from namel3ss.ui.manifest.canonical import _slugify


REQUIRED_CAPABILITY = "ui.custom_layouts"


def build_layout_manifest_document(
    page: ir.PageLayoutIR,
    *,
    capabilities: Iterable[str] | None = None,
    studio_mode: bool = False,
) -> dict:
    capability_set = {str(item).strip().lower() for item in capabilities or []}
    page_payload, actions = build_layout_manifest_page(
        page,
        capabilities=capability_set,
        studio_mode=studio_mode,
    )
    manifest = {
        "schema_version": "1",
        "mode": "studio" if studio_mode else "runtime",
        "capabilities": sorted(capability_set),
        "pages": [page_payload],
        "actions": actions,
        "layout_state": dict(page_payload.get("layout_state") or {}),
    }
    return manifest


def build_layout_manifest_page(
    page: ir.PageLayoutIR,
    *,
    capabilities: Iterable[str] | None = None,
    studio_mode: bool = False,
) -> tuple[dict, dict[str, dict]]:
    capability_set = {str(item).strip().lower() for item in capabilities or []}
    elements = [_node_to_manifest(node) for node in page.elements]
    _ensure_layout_capability(capability_set, studio_mode=studio_mode, has_layout_elements=bool(elements))

    page_slug = _slugify(page.name)
    drawer_by_trigger = _collect_drawer_targets(elements)
    sticky_ids = _collect_type_ids(elements, expected_type="layout.sticky")
    selection_paths = _collect_selection_paths(elements)
    actions, binding_actions = _build_actions_map(
        page_slug=page_slug,
        action_entries=page.actions,
        drawer_by_trigger=drawer_by_trigger,
        sticky_ids=sticky_ids,
        selection_paths=selection_paths,
    )
    _bind_action_ids(elements, binding_actions)
    layout_state = build_layout_state(elements)
    page_payload = {
        "name": page.name,
        "slug": page_slug,
        "elements": elements,
        "layout_state": layout_state,
    }
    return page_payload, actions


def _ensure_layout_capability(capabilities: set[str], *, studio_mode: bool, has_layout_elements: bool) -> None:
    if not has_layout_elements:
        return
    if studio_mode:
        return
    if REQUIRED_CAPABILITY in capabilities:
        return
    raise Namel3ssError(
        f'Custom layout rendering requires capability "{REQUIRED_CAPABILITY}" or Studio mode.',
        line=1,
        column=1,
    )


def _build_actions_map(
    *,
    page_slug: str,
    action_entries: Iterable[ir.ActionIR],
    drawer_by_trigger: dict[str, str],
    sticky_ids: list[str],
    selection_paths: list[str],
) -> tuple[dict[str, dict], dict[tuple[str, str, str], str]]:
    ordered_actions = list(action_entries)
    indexed: dict[str, dict] = {}
    binding_actions: dict[tuple[str, str, str], str] = {}
    click_action_ids = _click_action_ids(ordered_actions)
    order = 0
    for action in ordered_actions:
        mapped_type, mapped_target, shortcut = _map_action_type(action, drawer_by_trigger)
        payload = {"source_event": action.event}
        if mapped_type == "layout.drawer.open":
            payload["trigger_id"] = action.target
        if mapped_type == "layout.shortcut":
            dispatch_id = click_action_ids.get(action.node_id)
            payload["shortcut"] = action.target
            if dispatch_id:
                payload["dispatch_action_id"] = dispatch_id
        entry = build_layout_action_entry(
            action_id=action.id,
            action_type=mapped_type,
            target=mapped_target,
            event=action.event,
            node_id=action.node_id,
            payload=payload,
            line=action.line,
            column=action.column,
            order=order,
            shortcut=shortcut,
        )
        indexed[action.id] = normalize_action_entry(action.id, entry)
        binding_key = (action.node_id, action.event, action.target)
        binding_actions.setdefault(binding_key, action.id)
        order += 1

    for trigger_id, drawer_id in sorted(drawer_by_trigger.items()):
        open_id = f"page.{page_slug}.drawer.{_slugify(trigger_id)}.open"
        close_id = f"page.{page_slug}.drawer.{_slugify(trigger_id)}.close"
        toggle_id = f"page.{page_slug}.drawer.{_slugify(trigger_id)}.toggle"
        if open_id not in indexed:
            indexed[open_id] = normalize_action_entry(
                open_id,
                build_layout_action_entry(
                    action_id=open_id,
                    action_type="layout.drawer.open",
                    target=drawer_id,
                    payload={"trigger_id": trigger_id},
                    order=order,
                ),
            )
            order += 1
        if close_id not in indexed:
            indexed[close_id] = normalize_action_entry(
                close_id,
                build_layout_action_entry(
                    action_id=close_id,
                    action_type="layout.drawer.close",
                    target=drawer_id,
                    payload={"trigger_id": trigger_id},
                    order=order,
                ),
            )
            order += 1
        if toggle_id not in indexed:
            indexed[toggle_id] = normalize_action_entry(
                toggle_id,
                build_layout_action_entry(
                    action_id=toggle_id,
                    action_type="layout.drawer.toggle",
                    target=drawer_id,
                    payload={"trigger_id": trigger_id},
                    order=order,
                ),
            )
            order += 1

    for sticky_id in sorted(sticky_ids):
        for suffix, action_type in (
            ("show", "layout.sticky.show"),
            ("hide", "layout.sticky.hide"),
            ("toggle", "layout.sticky.toggle"),
        ):
            action_id = f"page.{page_slug}.sticky.{_slugify(sticky_id)}.{suffix}"
            indexed[action_id] = normalize_action_entry(
                action_id,
                build_layout_action_entry(
                    action_id=action_id,
                    action_type=action_type,
                    target=sticky_id,
                    order=order,
                ),
            )
            order += 1

    for path in sorted(selection_paths):
        action_id = f"page.{page_slug}.selection.{_slugify(path)}.set"
        indexed[action_id] = normalize_action_entry(
            action_id,
            build_layout_action_entry(
                action_id=action_id,
                action_type="layout.selection.set",
                payload={"path": path},
                order=order,
            ),
        )
        indexed[action_id]["path"] = path
        order += 1

    sorted_entries = sorted(indexed.items(), key=lambda item: _action_sort_key(item[1]))
    return ({action_id: entry for action_id, entry in sorted_entries}, binding_actions)


def _click_action_ids(action_entries: Iterable[ir.ActionIR]) -> dict[str, str]:
    result: dict[str, str] = {}
    for action in action_entries:
        if action.event != "click":
            continue
        if not action.node_id:
            continue
        result.setdefault(action.node_id, action.id)
    return result


def _map_action_type(action: ir.ActionIR, drawer_by_trigger: Mapping[str, str]) -> tuple[str, str | None, str | None]:
    if action.event == "click" and action.target in drawer_by_trigger:
        return "layout.drawer.open", drawer_by_trigger[action.target], None
    if action.event == "keyboard_shortcut":
        return "layout.shortcut", action.target, action.target
    return "layout.interaction", action.target, None


def _action_sort_key(action: Mapping[str, object]) -> tuple[int, int, int, str]:
    order = int(action.get("order", 0)) if isinstance(action.get("order"), int) else 0
    line = int(action.get("line", 0)) if isinstance(action.get("line"), int) else 0
    column = int(action.get("column", 0)) if isinstance(action.get("column"), int) else 0
    action_id = str(action.get("id") or "")
    return (order, line, column, action_id)


def _collect_drawer_targets(elements: list[dict]) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in _iter_elements(elements):
        if node.get("type") != "layout.drawer":
            continue
        trigger_id = node.get("trigger_id")
        element_id = node.get("id")
        if not isinstance(trigger_id, str) or not trigger_id:
            continue
        if not isinstance(element_id, str) or not element_id:
            continue
        result[trigger_id] = element_id
    return result


def _collect_type_ids(elements: list[dict], *, expected_type: str) -> list[str]:
    ids: list[str] = []
    for node in _iter_elements(elements):
        if node.get("type") != expected_type:
            continue
        element_id = node.get("id")
        if isinstance(element_id, str) and element_id:
            ids.append(element_id)
    return ids


def _collect_selection_paths(elements: list[dict]) -> list[str]:
    paths: list[str] = []
    for node in _iter_elements(elements):
        bindings = node.get("bindings")
        if not isinstance(bindings, Mapping):
            continue
        selected = bindings.get("selected_item")
        if isinstance(selected, str) and selected:
            paths.append(selected)
    return paths


def _iter_elements(elements: Iterable[dict]) -> Iterable[dict]:
    queue: list[dict] = [node for node in elements if isinstance(node, dict)]
    while queue:
        node = queue.pop(0)
        yield node
        for key in ("children", "primary", "secondary", "left", "center", "right", "sidebar", "main"):
            child_list = node.get(key)
            if not isinstance(child_list, list):
                continue
            for child in child_list:
                if isinstance(child, dict):
                    queue.append(child)


def _bind_action_ids(elements: list[dict], binding_actions: Mapping[tuple[str, str, str], str]) -> None:
    for node in _iter_elements(elements):
        node_id = node.get("id")
        bindings = node.get("bindings")
        if not isinstance(node_id, str) or not node_id:
            continue
        if not isinstance(bindings, dict):
            continue
        click_target = bindings.get("on_click")
        if isinstance(click_target, str) and click_target:
            key = (node_id, "click", click_target)
            action_id = binding_actions.get(key)
            if isinstance(action_id, str) and action_id:
                bindings["on_click"] = action_id


def _node_to_manifest(node: ir.LayoutElementIR) -> dict:
    base = {
        "id": node.id,
        "bindings": {
            "on_click": node.bindings.on_click,
            "keyboard_shortcut": node.bindings.keyboard_shortcut,
            "selected_item": node.bindings.selected_item,
        },
        "line": node.line,
        "column": node.column,
    }
    if isinstance(node, ir.SidebarIR):
        return {**base, "type": "layout.sidebar", "children": [_node_to_manifest(child) for child in node.children]}
    if isinstance(node, ir.MainIR):
        return {**base, "type": "layout.main", "children": [_node_to_manifest(child) for child in node.children]}
    if isinstance(node, ir.DrawerIR):
        return {
            **base,
            "type": "layout.drawer",
            "side": node.side,
            "trigger_id": node.trigger_id,
            "open_state": False,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.StickyIR):
        return {
            **base,
            "type": "layout.sticky",
            "position": node.position,
            "visible": True,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.ScrollAreaIR):
        return {**base, "type": "layout.scroll_area", "axis": node.axis, "children": [_node_to_manifest(child) for child in node.children]}
    if isinstance(node, ir.TwoPaneIR):
        return {
            **base,
            "type": "layout.two_pane",
            "primary": [_node_to_manifest(child) for child in node.primary],
            "secondary": [_node_to_manifest(child) for child in node.secondary],
        }
    if isinstance(node, ir.ThreePaneIR):
        return {
            **base,
            "type": "layout.three_pane",
            "left": [_node_to_manifest(child) for child in node.left],
            "center": [_node_to_manifest(child) for child in node.center],
            "right": [_node_to_manifest(child) for child in node.right],
        }
    if isinstance(node, ir.FormIR):
        return {
            **base,
            "type": "component.form",
            "name": node.name,
            "wizard": node.wizard,
            "sections": list(node.sections),
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.TableIR):
        return {
            **base,
            "type": "component.table",
            "name": node.name,
            "reorderable_columns": node.reorderable_columns,
            "fixed_header": node.fixed_header,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.CardIR):
        return {
            **base,
            "type": "component.card",
            "name": node.name,
            "expandable": node.expandable,
            "collapsed": node.collapsed,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.NavigationTabsIR):
        return {
            **base,
            "type": "component.tabs",
            "name": node.name,
            "dynamic_from_state": node.dynamic_from_state,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.MediaIR):
        return {
            **base,
            "type": "component.media",
            "name": node.name,
            "inline_crop": node.inline_crop,
            "annotation": node.annotation,
            "children": [_node_to_manifest(child) for child in node.children],
        }
    if isinstance(node, ir.LiteralItemIR):
        return {**base, "type": "component.literal", "text": node.text}
    raise TypeError(f"Unsupported layout node type: {type(node)!r}")


__all__ = [
    "REQUIRED_CAPABILITY",
    "build_layout_manifest_document",
    "build_layout_manifest_page",
]
