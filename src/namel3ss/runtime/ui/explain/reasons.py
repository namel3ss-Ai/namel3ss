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


def declared_in_pattern(origin: dict) -> str | None:
    if not isinstance(origin, dict):
        return None
    pattern = origin.get("pattern")
    invocation = origin.get("invocation")
    element = origin.get("element")
    if not pattern:
        return None
    if invocation and element:
        return f'from pattern "{pattern}" invocation "{invocation}" element "{element}"'
    if invocation:
        return f'from pattern "{pattern}" invocation "{invocation}"'
    return f'from pattern "{pattern}"'


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


def visibility_reasons(visibility: dict | None, visible: bool) -> list[str]:
    if visibility is None:
        return [] if visible else ["hidden because parent visibility is false"]
    reasons: list[str] = []
    predicate = visibility.get("predicate") if isinstance(visibility, dict) else None
    state_paths = visibility.get("state_paths") if isinstance(visibility, dict) else None
    result = visibility.get("result") if isinstance(visibility, dict) else None
    if predicate:
        reasons.append(f"visibility predicate {predicate}")
    if state_paths:
        joined = ", ".join(str(path) for path in state_paths)
        reasons.append(f"visibility paths {joined}")
    if isinstance(result, bool):
        result_text = "true" if result else "false"
        reasons.append(f"visibility result {result_text}")
    if visible:
        if isinstance(result, bool):
            reasons.append("visible because visibility result is true")
    else:
        if result is False:
            reasons.append("hidden because visibility result is false")
        else:
            reasons.append("hidden because parent visibility is false")
    return reasons


__all__ = [
    "ACTION_AVAILABLE",
    "ACTION_NOT_AVAILABLE",
    "ACTION_UNKNOWN",
    "action_reason_line",
    "action_status",
    "declared_in_pack",
    "declared_in_pattern",
    "declared_in_page",
    "evaluate_requires",
    "format_requires",
    "visibility_reasons",
]
