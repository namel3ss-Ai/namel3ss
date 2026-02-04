from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.ui_mode import render_manifest
from namel3ss.config.loader import load_config
from namel3ss.runtime.identity.context import resolve_identity

from .build_redaction import _bound_to, _element_fix_hint, _element_label
from .build_sections import (
    _card_reasons,
    _chart_reasons,
    _chat_item_reasons,
    _chat_reasons,
    _form_reasons,
    _list_reasons,
    _overlay_reasons,
    _table_reasons,
    _tabs_reasons,
    _upload_reasons,
)
from .model import UIActionState, UIElementState, UIExplainPack
from .normalize import build_plain_text, write_last_ui
from .reasons import (
    ACTION_AVAILABLE,
    ACTION_NOT_AVAILABLE,
    action_reason_line,
    action_status,
    availability_reasons,
    declared_in_pack,
    declared_in_pattern,
    declared_in_page,
    evaluate_requires,
    format_requires,
    visibility_reasons,
)
from .render_plain import render_see

API_VERSION = "ui"


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
        availability = entry.get("availability") if isinstance(entry, dict) else None
        enabled_flag = entry.get("enabled") if isinstance(entry, dict) else None
        requires_expr = flow_requires.get(flow) if flow else None
        requires_text = format_requires(requires_expr)
        evaluated = evaluate_requires(requires_expr, identity, state)
        status, reason_list = action_status(requires_text, evaluated)
        reasons = availability_reasons(availability, enabled_flag if isinstance(enabled_flag, bool) else None)
        reasons.extend(reason_list)
        if enabled_flag is False:
            status = ACTION_NOT_AVAILABLE
        if action_type == "upload_select":
            reasons.append("upload selected (metadata only)")
        if action_type == "ingestion_run":
            reasons.append("ingestion run (quality gate recorded)")
        if action_type == "ingestion_review":
            reasons.append("ingestion review (read-only reports)")
        if action_type == "ingestion_skip":
            reasons.append("ingestion skip (explicit exclusion)")
        if action_type == "retrieval_run":
            reasons.append("retrieval run (quality-aware ordering)")
        if action_type == "upload_replace":
            reasons.append("upload replace (placeholder)")
        items.append(
            UIActionState(
                id=action_id,
                type=action_type,
                status=status,
                flow=flow,
                record=record,
                requires=requires_text,
                reasons=reasons,
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
    fix_hint = _element_fix_hint(kind, element)
    accessibility = element.get("accessibility") if isinstance(element, dict) else None
    reasons = [declared_in_page(page_name)]
    origin_reason = declared_in_pack(element.get("origin"))
    if origin_reason:
        reasons.append(origin_reason)
    pattern_reason = declared_in_pattern(element.get("origin"))
    if pattern_reason:
        reasons.append(pattern_reason)
    visible = element.get("visible", True) is not False
    reasons.extend(visibility_reasons(element.get("visibility"), visible))
    enabled: bool | None = None

    action_id = element.get("action_id") or element.get("id")
    if action_id and action_id in action_map:
        action = action_map[action_id]
        enabled = _enabled_from_status(action.status)
        reasons.append(action_reason_line(action_id, action.status, action.requires, None))
    if kind == "story_step":
        gate = element.get("gate") if isinstance(element, dict) else None
        if gate:
            ready = gate.get("ready")
            if ready is not None:
                enabled = bool(ready)
            requires_text = gate.get("requires") or gate.get("reason")
            status, reason_list = action_status(requires_text, ready)
            reasons.append(action_reason_line(element_id, status, requires_text, ready))
            for reason in reason_list:
                if reason not in reasons:
                    reasons.append(reason)
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
    if kind == "upload":
        reasons.extend(_upload_reasons(element))
    return UIElementState(
        id=element_id,
        kind=kind,
        label=label,
        visible=visible,
        enabled=enabled,
        bound_to=bound_to,
        fix_hint=fix_hint,
        accessibility=accessibility,
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


def _summary_text(page_count: int, element_count: int, action_count: int) -> str:
    return f"UI: {page_count} pages, {element_count} elements, {action_count} actions."


__all__ = ["API_VERSION", "build_ui_explain_pack", "write_ui_explain_artifacts"]
