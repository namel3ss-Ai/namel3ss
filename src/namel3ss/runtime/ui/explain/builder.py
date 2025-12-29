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
    declared_in_page,
    evaluate_requires,
    format_requires,
)
from .render_plain import render_see

API_VERSION = "ui.v1"


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
    enabled: bool | None = None

    action_id = element.get("action_id") or element.get("id")
    if action_id and action_id in action_map:
        action = action_map[action_id]
        enabled = _enabled_from_status(action.status)
        reasons.append(action_reason_line(action_id, action.status, action.requires, None))
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
    if kind in {"button", "section", "card"}:
        return element.get("label")
    if kind == "image":
        return element.get("alt") or element.get("src")
    return None


def _bound_to(kind: str, element: dict) -> str | None:
    if kind in {"form", "table"}:
        record = element.get("record")
        if record:
            return f"record:{record}"
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


def _summary_text(page_count: int, element_count: int, action_count: int) -> str:
    return f"UI: {page_count} pages, {element_count} elements, {action_count} actions."


__all__ = ["API_VERSION", "build_ui_explain_pack", "write_ui_explain_artifacts"]
