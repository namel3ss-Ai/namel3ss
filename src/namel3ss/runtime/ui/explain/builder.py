from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.ui_mode import render_manifest
from namel3ss.config.loader import load_config
from namel3ss.runtime.identity.context import resolve_identity

from .model import UIActionState, UIElementState, UIExplainPack
from .normalize import build_plain_text, write_last_ui
from .reasons import (
    ACTION_AVAILABLE,
    ACTION_NOT_AVAILABLE,
    action_reason_line,
    action_status,
    declared_in_pack,
    declared_in_page,
    evaluate_requires,
    format_requires,
)
from .render_plain import render_see

API_VERSION = "ui.v1"
_MAX_REASON_ITEMS = 8


def _join_limited(items: list[str], *, sep: str = ", ") -> str:
    filtered = [str(item) for item in items if item]
    if not filtered:
        return ""
    if len(filtered) <= _MAX_REASON_ITEMS:
        return sep.join(filtered)
    head = filtered[:_MAX_REASON_ITEMS]
    remaining = len(filtered) - _MAX_REASON_ITEMS
    return f"{sep.join(head)}{sep}... (+{remaining} more)"


def build_ui_explain_pack(project_root: Path, app_path: str) -> dict:
    program_ir, _sources = load_program(app_path)
    manifest = render_manifest(program_ir)
    config = load_config(app_path=Path(app_path), root=project_root)
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    state: dict = {}

    flow_requires = _flow_requires(program_ir)
    actions = _build_actions(manifest, flow_requires, identity, state)
    elements, pages = _build_pages(manifest, actions)
    what_not = _build_what_not(actions)

    summary = _summary_text(len(pages), len(elements), len(actions))
    pack = UIExplainPack(
        ok=True,
        api_version=API_VERSION,
        pages=pages,
        actions=[action.as_dict() for action in actions],
        summary=summary,
        what_not=what_not,
    )
    return pack.as_dict()


def write_ui_explain_artifacts(root: Path, pack: dict) -> str:
    text = render_see(pack)
    plain = build_plain_text(pack)
    write_last_ui(root, pack, plain, text)
    return text


def _flow_requires(program_ir) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for flow in getattr(program_ir, "flows", []):
        mapping[flow.name] = getattr(flow, "requires", None)
    return mapping


def _build_actions(manifest: dict, flow_requires: dict[str, object], identity: dict, state: dict) -> list[UIActionState]:
    actions = manifest.get("actions") or {}
    items: list[UIActionState] = []
    for action_id in sorted(actions.keys()):
        entry = actions[action_id]
        action_type = str(entry.get("type") or "")
        flow = entry.get("flow") if action_type == "call_flow" else None
        record = entry.get("record") if action_type == "submit_form" else None
        requires_expr = flow_requires.get(flow) if flow else None
        requires_text = format_requires(requires_expr)
        evaluated = evaluate_requires(requires_expr, identity, state)
        status, reason_list = action_status(requires_text, evaluated)
        items.append(
            UIActionState(
                id=action_id,
                type=action_type,
                status=status,
                flow=flow,
                record=record,
                requires=requires_text,
                reasons=reason_list,
            )
        )
    return items


def _build_pages(manifest: dict, actions: list[UIActionState]) -> tuple[list[UIElementState], list[dict]]:
    pages = manifest.get("pages") or []
    action_map = {action.id: action for action in actions}

    element_states: list[UIElementState] = []
    page_entries: list[dict] = []
    for page in pages:
        page_name = page.get("name") or ""
        counter = 0
        elements: list[dict] = []
        for element in _walk_elements(page.get("elements") or []):
            counter += 1
            state = _element_state(page_name, counter, element, action_map)
            element_states.append(state)
            elements.append(state.as_dict())
        page_entries.append({"name": page_name, "elements": elements})
    return element_states, page_entries


def _element_state(
    page_name: str,
    counter: int,
    element: dict,
    action_map: dict[str, UIActionState],
) -> UIElementState:
    kind = str(element.get("type") or "item")
    element_id = f"page:{page_name}:item:{counter}:{kind}"
    label = _element_label(kind, element)
    bound_to = _bound_to(kind, element)
    reasons = [declared_in_page(page_name)]
    origin_reason = declared_in_pack(element.get("origin"))
    if origin_reason:
        reasons.append(origin_reason)
    enabled: bool | None = None

    action_id = element.get("action_id") or element.get("id")
    if action_id and action_id in action_map:
        action = action_map[action_id]
        enabled = _enabled_from_status(action.status)
        reasons.append(action_reason_line(action_id, action.status, action.requires, None))
    if kind == "table":
        reasons.extend(_table_reasons(element))
    if kind == "list":
        reasons.extend(_list_reasons(element))
    if kind == "chart":
        reasons.extend(_chart_reasons(element))
    if kind == "form":
        reasons.extend(_form_reasons(element))
    if kind == "chat":
        reasons.extend(_chat_reasons(element))
    if kind in {"messages", "composer", "thinking", "citations", "memory"}:
        reasons.extend(_chat_item_reasons(element))
    if kind == "tabs":
        reasons.extend(_tabs_reasons(element))
    if kind in {"modal", "drawer"}:
        reasons.extend(_overlay_reasons(element))
    if kind == "card":
        reasons.extend(_card_reasons(element))
    return UIElementState(
        id=element_id,
        kind=kind,
        label=label,
        visible=True,
        enabled=enabled,
        bound_to=bound_to,
        reasons=reasons,
    )


def _walk_elements(elements: list[dict]) -> list[dict]:
    items: list[dict] = []
    for element in elements:
        items.append(element)
        children = element.get("children")
        if isinstance(children, list) and children:
            items.extend(_walk_elements(children))
    return items


def _element_label(kind: str, element: dict) -> str | None:
    if kind in {"title", "text"}:
        return element.get("value")
    if kind in {"button", "section", "card", "tab", "modal", "drawer"}:
        return element.get("label")
    if kind in {"messages", "citations", "memory"}:
        return element.get("source")
    if kind == "composer":
        return element.get("flow")
    if kind == "thinking":
        return element.get("when")
    if kind == "image":
        return element.get("alt") or element.get("src")
    if kind == "chart":
        return element.get("explain") or element.get("record") or element.get("source")
    return None


def _bound_to(kind: str, element: dict) -> str | None:
    if kind in {"form", "table", "list"}:
        record = element.get("record")
        if record:
            return f"record:{record}"
    if kind in {"messages", "citations", "memory"}:
        source = element.get("source")
        if source:
            return source
    if kind == "thinking":
        when = element.get("when")
        if when:
            return when
    if kind == "composer":
        flow = element.get("flow")
        if flow:
            return f"flow:{flow}"
    if kind == "chart":
        record = element.get("record")
        if record:
            return f"record:{record}"
        source = element.get("source")
        if source:
            return source
    return None


def _enabled_from_status(status: str) -> bool | None:
    if status == ACTION_AVAILABLE:
        return True
    if status == ACTION_NOT_AVAILABLE:
        return False
    return None


def _build_what_not(actions: list[UIActionState]) -> list[str]:
    lines: list[str] = []
    for action in actions:
        if action.status != ACTION_NOT_AVAILABLE:
            continue
        requires = action.requires
        if requires:
            lines.append(f"Action {action.id} not available because requires {requires}.")
    return lines


def _table_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    columns = element.get("columns") or []
    if columns and element.get("columns_configured"):
        labels = []
        for col in columns:
            name = col.get("name")
            label = col.get("label")
            if label and label != name:
                labels.append(f"{name} ({label})")
            elif name:
                labels.append(str(name))
        if labels:
            joined = _join_limited(labels)
            if joined:
                reasons.append(f"columns: {joined}")
    sort = element.get("sort")
    if isinstance(sort, dict):
        by = sort.get("by")
        order = sort.get("order")
        if by and order:
            reasons.append(f"sort: {by} {order}")
    pagination = element.get("pagination")
    if isinstance(pagination, dict) and pagination.get("page_size") is not None:
        reasons.append(f"pagination: page_size={pagination.get('page_size')}")
    selection = element.get("selection")
    if selection is not None:
        reasons.append(f"selection (ui): {selection}")
    empty_text = element.get("empty_text")
    if empty_text:
        reasons.append(f"empty state: {empty_text}")
    row_actions = element.get("row_actions") or []
    if row_actions:
        labels = [action.get("label") for action in row_actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"row actions: {joined}")
    return reasons


def _list_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    variant = element.get("variant")
    if variant:
        reasons.append(f"variant: {variant}")
    mapping = element.get("item")
    if isinstance(mapping, dict):
        parts = []
        for key in ("primary", "secondary", "meta", "icon"):
            value = mapping.get(key)
            if value:
                parts.append(f"{key}={value}")
        joined = _join_limited(parts)
        if joined:
            reasons.append(f"item: {joined}")
    selection = element.get("selection")
    if selection is not None:
        reasons.append(f"selection (ui): {selection}")
    empty_text = element.get("empty_text")
    if empty_text:
        reasons.append(f"empty state: {empty_text}")
    actions = element.get("actions") or []
    if actions:
        labels = [action.get("label") for action in actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"actions: {joined}")
    return reasons


def _chart_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    chart_type = element.get("chart_type")
    if chart_type:
        reasons.append(f"type: {chart_type}")
    x = element.get("x")
    y = element.get("y")
    if x or y:
        parts = []
        if x:
            parts.append(f"x={x}")
        if y:
            parts.append(f"y={y}")
        reasons.append(f"mapping: {', '.join(parts)}")
    explain = element.get("explain")
    if explain:
        reasons.append(f"explain: {explain}")
    return reasons


def _tabs_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    labels = element.get("tabs")
    if isinstance(labels, list) and labels:
        joined = _join_limited([str(label) for label in labels])
        if joined:
            reasons.append(f"tabs: {joined}")
    default_label = element.get("default")
    if default_label:
        reasons.append(f"default: {default_label}")
    active_label = element.get("active")
    if active_label:
        reasons.append(f"active (ui): {active_label}")
    return reasons


def _overlay_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    open_state = element.get("open")
    if isinstance(open_state, bool):
        reasons.append(f"open (ui): {str(open_state).lower()}")
    open_actions = element.get("open_actions") or []
    if open_actions:
        joined = _join_limited([str(action) for action in open_actions])
        if joined:
            reasons.append(f"open actions (ui): {joined}")
    close_actions = element.get("close_actions") or []
    if close_actions:
        joined = _join_limited([str(action) for action in close_actions])
        if joined:
            reasons.append(f"close actions (ui): {joined}")
    return reasons


def _chat_reasons(element: dict) -> list[str]:
    return []


def _chat_item_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    kind = element.get("type")
    if kind == "composer":
        flow = element.get("flow")
        if flow:
            reasons.append(f"calls flow: {flow}")
    if kind == "thinking":
        active = element.get("active")
        if isinstance(active, bool):
            reasons.append(f"active (ui): {str(active).lower()}")
    if kind == "memory":
        lane = element.get("lane")
        if lane:
            reasons.append(f"lane: {lane}")
    return reasons


def _form_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    groups = element.get("groups")
    if isinstance(groups, list) and groups:
        parts = []
        for group in groups:
            label = group.get("label") or ""
            fields = group.get("fields") or []
            if fields:
                parts.append(f"{label}: {', '.join(str(name) for name in fields)}")
            else:
                parts.append(label)
        joined = _join_limited(parts, sep="; ")
        if joined:
            reasons.append(f"groups: {joined}")
    fields = element.get("fields") or []
    help_fields = [field.get("name") for field in fields if field.get("help")]
    if help_fields:
        joined = _join_limited([str(name) for name in help_fields if name])
        if joined:
            reasons.append(f"help: {joined}")
    readonly_fields = [field.get("name") for field in fields if field.get("readonly")]
    if readonly_fields:
        joined = _join_limited([str(name) for name in readonly_fields if name])
        if joined:
            reasons.append(f"readonly: {joined}")
    constraint_lines = []
    for field in fields:
        constraints = field.get("constraints") or []
        if not constraints:
            continue
        name = field.get("name")
        entries = [_format_constraint(entry) for entry in constraints]
        entries = [entry for entry in entries if entry]
        if name and entries:
            constraint_lines.append(f"{name} ({', '.join(entries)})")
    joined = _join_limited(constraint_lines)
    if joined:
        reasons.append(f"constraints: {joined}")
    return reasons


def _format_constraint(constraint: dict) -> str:
    kind = constraint.get("kind")
    if not kind:
        return ""
    if kind in {"present", "unique", "integer"}:
        return kind
    if kind in {"pattern", "greater_than", "at_least", "less_than", "at_most", "length_min", "length_max"}:
        value = constraint.get("value")
        if value is None:
            return kind
        return f"{kind} {value}"
    if kind == "between":
        return f"between {constraint.get('min')} and {constraint.get('max')}"
    return str(kind)


def _card_reasons(element: dict) -> list[str]:
    reasons: list[str] = []
    stat = element.get("stat")
    if isinstance(stat, dict):
        label = stat.get("label")
        source = stat.get("source")
        if label and source:
            reasons.append(f"stat: {label} = {source}")
        elif source:
            reasons.append(f"stat: {source}")
        elif label:
            reasons.append(f"stat: {label}")
    actions = element.get("actions") or []
    if actions:
        labels = [action.get("label") for action in actions if action.get("label")]
        joined = _join_limited(labels)
        if joined:
            reasons.append(f"actions: {joined}")
    return reasons


def _summary_text(page_count: int, element_count: int, action_count: int) -> str:
    return f"UI: {page_count} pages, {element_count} elements, {action_count} actions."


__all__ = ["API_VERSION", "build_ui_explain_pack", "write_ui_explain_artifacts"]
