from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.normalize import format_expression
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.identity.guards import build_guard_context


ACTION_AVAILABLE = "available"
ACTION_NOT_AVAILABLE = "not available"
ACTION_UNKNOWN = "unknown"


def declared_in_page(page_name: str) -> str:
    return f'declared in page "{page_name}"'


def declared_in_pack(origin: dict) -> str | None:
    if not isinstance(origin, dict):
        return None
    pack = origin.get("pack")
    fragment = origin.get("fragment")
    version = origin.get("version")
    if not pack or not fragment:
        return None
    if version:
        return f'from ui_pack "{pack}" ({version}) fragment "{fragment}"'
    return f'from ui_pack "{pack}" fragment "{fragment}"'


def format_requires(expr: ir.Expression | None) -> str | None:
    if expr is None:
        return None
    return format_expression(expr)


def evaluate_requires(expr: ir.Expression | None, identity: dict, state: dict | None) -> bool | None:
    if expr is None:
        return None
    ctx = build_guard_context(identity=identity, state=state or {})
    try:
        result = evaluate_expression(ctx, expr)
    except Namel3ssError:
        return None
    if isinstance(result, bool):
        return result
    return None


def action_status(requires_text: str | None, evaluated: bool | None) -> tuple[str, list[str]]:
    if not requires_text:
        return ACTION_AVAILABLE, []
    if evaluated is True:
        return ACTION_AVAILABLE, [f"requires {requires_text}"]
    if evaluated is False:
        return ACTION_NOT_AVAILABLE, [f"requires {requires_text}"]
    return ACTION_UNKNOWN, [f"requires {requires_text} (not evaluated)"]


def action_reason_line(action_id: str, status: str, requires_text: str | None, evaluated: bool | None) -> str:
    if status == ACTION_AVAILABLE:
        return f'action "{action_id}" is available'
    if status == ACTION_NOT_AVAILABLE:
        if requires_text:
            return f'action "{action_id}" not available because requires {requires_text}'
        return f'action "{action_id}" not available'
    if requires_text:
        return f'action "{action_id}" may require {requires_text} (not evaluated)'
    return f'action "{action_id}" availability is unknown'


__all__ = [
    "ACTION_AVAILABLE",
    "ACTION_NOT_AVAILABLE",
    "ACTION_UNKNOWN",
    "action_reason_line",
    "action_status",
    "declared_in_pack",
    "declared_in_page",
    "evaluate_requires",
    "format_requires",
]
