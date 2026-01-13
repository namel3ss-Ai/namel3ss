from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.validation import ValidationMode, add_warning


@dataclass
class GuardContext:
    locals: dict
    state: dict
    identity: dict


def enforce_requires(
    ctx: object,
    expr: ir.Expression | None,
    *,
    subject: str,
    line: int | None,
    column: int | None,
    mode: ValidationMode = ValidationMode.RUNTIME,
    warnings: list | None = None,
) -> None:
    if expr is None:
        return
    if mode == ValidationMode.STATIC:
        add_warning(
            warnings,
            code="requires.skipped",
            message=f"{subject} requires check deferred to runtime.",
            fix="Provide identity/state at runtime that satisfies the requires expression.",
            line=line,
            column=column,
            enforced_at="runtime",
        )
        return
    result = evaluate_expression(ctx, expr)
    if not isinstance(result, bool):
        raise Namel3ssError(
            _requires_type_message(subject, result),
            line=line,
            column=column,
        )
    if not result:
        raise Namel3ssError(
            _requires_failed_message(subject),
            line=line,
            column=column,
            details={"category": "policy"},
        )


def build_guard_context(*, identity: dict, state: dict | None = None) -> GuardContext:
    return GuardContext(locals={}, state=state or {}, identity=identity)


def _requires_type_message(subject: str, value: object) -> str:
    kind = _value_kind(value)
    return build_guidance_message(
        what=f"{subject} requires a boolean condition.",
        why=f"The requires expression evaluated to {kind}, not true/false.",
        fix="Use a comparison so the requires clause evaluates to true/false.",
        example='requires identity.role is "admin"',
    )


def _requires_failed_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} access is not permitted.",
        why="The requires condition evaluated to false.",
        fix="Provide an identity that satisfies the requirement or update the requires clause.",
        example='requires identity.role is "admin"',
    )


def _value_kind(value: object) -> str:
    from namel3ss.utils.numbers import is_number

    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return type(value).__name__
