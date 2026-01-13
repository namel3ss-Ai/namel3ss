from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.explain import format_expression_canonical
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.identity.guards import build_guard_context
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode, add_warning
from namel3ss.ui.manifest_overlay import _drawer_id, _modal_id


def _card_action_id(element_id: str, label: str) -> str:
    return f"{element_id}.action.{_slugify(label)}"


def _build_card_actions(element_id: str, page_slug: str, actions: list[ir.CardAction]) -> tuple[list[dict], Dict[str, dict]]:
    seen: set[str] = set()
    entries: list[dict] = []
    action_map: Dict[str, dict] = {}
    for action in actions:
        action_id = _card_action_id(element_id, action.label)
        if action_id in seen:
            raise Namel3ssError(
                f"Card action '{action.label}' collides with another action id",
                line=action.line,
                column=action.column,
            )
        seen.add(action_id)
        if action.kind == "call_flow":
            entry = {"id": action_id, "type": "call_flow", "flow": action.flow_name}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "flow": action.flow_name})
            continue
        if action.kind in {"open_modal", "close_modal"}:
            target = _modal_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        if action.kind in {"open_drawer", "close_drawer"}:
            target = _drawer_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        raise Namel3ssError(
            f"Card action '{action.label}' is not supported",
            line=action.line,
            column=action.column,
        )
    return entries, action_map


def _build_card_stat(
    stat: ir.CardStat,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> dict:
    ctx = build_guard_context(identity=identity or {}, state=state_ctx.state)
    try:
        value = evaluate_expression(ctx, stat.value)
    except Namel3ssError as err:
        if mode == ValidationMode.STATIC:
            add_warning(
                warnings,
                code="state.eval.missing",
                message=str(err),
                fix="Declare a state default for the referenced path to make the stat safe in static validation.",
                line=stat.line,
                column=stat.column,
                enforced_at="runtime",
            )
            value = None
        else:
            raise
    payload = {"value": value, "source": format_expression_canonical(stat.value)}
    if stat.label is not None:
        payload["label"] = stat.label
    return payload


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed


__all__ = ["_build_card_actions", "_build_card_stat"]
