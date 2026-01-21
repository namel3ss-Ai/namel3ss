from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.auth.trace_events import authorization_check_event
from namel3ss.validation import ValidationMode, add_warning


@dataclass
class GuardContext:
    locals: dict
    state: dict
    identity: dict
    auth_context: object | None = None
    traces: list | None = None


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
        _record_auth_check(ctx, subject, outcome="invalid")
        raise Namel3ssError(
            _requires_type_message(subject, result),
            line=line,
            column=column,
        )
    if not result:
        message, category, reason = _requires_auth_message(subject, expr, ctx)
        _record_auth_check(ctx, subject, outcome="denied", reason=reason)
        raise Namel3ssError(
            message,
            line=line,
            column=column,
            details={"category": category, "reason_code": reason} if category else {"category": "policy"},
        )
    _record_auth_check(ctx, subject, outcome="allowed")


def build_guard_context(
    *,
    identity: dict,
    state: dict | None = None,
    auth_context: object | None = None,
    traces: list | None = None,
) -> GuardContext:
    return GuardContext(locals={}, state=state or {}, identity=identity, auth_context=auth_context, traces=traces)


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


def _requires_auth_message(subject: str, expr: ir.Expression, ctx: object) -> tuple[str, str | None, str | None]:
    if not requires_mentions_identity(expr):
        return _requires_failed_message(subject), "policy", "access_denied"
    auth_ctx = getattr(ctx, "auth_context", None)
    auth_error = getattr(auth_ctx, "error", None) if auth_ctx is not None else None
    authenticated = bool(getattr(auth_ctx, "authenticated", False)) if auth_ctx is not None else False
    if auth_error == "missing_authentication":
        return _missing_authentication_message(subject), "authentication", "missing_authentication"
    if auth_error == "token_invalid":
        return _token_invalid_message(subject), "authentication", "token_invalid"
    if auth_error == "token_expired":
        return _token_expired_message(subject), "authentication", "token_expired"
    if auth_error == "session_invalid":
        return _session_revoked_message(subject), "authentication", "session_revoked"
    if auth_error == "session_revoked":
        return _session_revoked_message(subject), "authentication", "session_revoked"
    if auth_error == "session_expired":
        return _session_expired_message(subject), "authentication", "session_expired"
    if authenticated:
        return _insufficient_permissions_message(subject), "permission", "insufficient_permissions"
    return _requires_failed_message(subject), "policy", "access_denied"


def _record_auth_check(ctx: object, subject: str, *, outcome: str, reason: str | None = None) -> None:
    traces = getattr(ctx, "traces", None)
    if not isinstance(traces, list):
        return
    traces.append(authorization_check_event(subject=subject, outcome=outcome, reason=reason))


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


def requires_mentions_identity(expr: ir.Expression | None) -> bool:
    if expr is None:
        return False
    if isinstance(expr, ir.VarReference):
        return expr.name == "identity"
    if isinstance(expr, ir.AttrAccess):
        return expr.base == "identity"
    if isinstance(expr, ir.UnaryOp):
        return requires_mentions_identity(expr.operand)
    if isinstance(expr, ir.BinaryOp):
        return requires_mentions_identity(expr.left) or requires_mentions_identity(expr.right)
    if isinstance(expr, ir.Comparison):
        return requires_mentions_identity(expr.left) or requires_mentions_identity(expr.right)
    if isinstance(expr, ir.ToolCallExpr):
        return any(requires_mentions_identity(arg.value) for arg in expr.arguments)
    if isinstance(expr, ir.BuiltinCallExpr):
        if expr.name in {"has_role", "has_permission"}:
            return True
        return any(requires_mentions_identity(arg) for arg in expr.arguments)
    if isinstance(expr, ir.ListExpr):
        return any(requires_mentions_identity(item) for item in expr.items)
    if isinstance(expr, ir.MapExpr):
        return any(
            requires_mentions_identity(entry.key) or requires_mentions_identity(entry.value)
            for entry in expr.entries
        )
    if isinstance(expr, ir.ListOpExpr):
        return (
            requires_mentions_identity(expr.target)
            or (expr.value is not None and requires_mentions_identity(expr.value))
            or (expr.index is not None and requires_mentions_identity(expr.index))
        )
    if isinstance(expr, ir.ListMapExpr):
        return requires_mentions_identity(expr.target) or requires_mentions_identity(expr.body)
    if isinstance(expr, ir.ListFilterExpr):
        return requires_mentions_identity(expr.target) or requires_mentions_identity(expr.predicate)
    if isinstance(expr, ir.ListReduceExpr):
        return (
            requires_mentions_identity(expr.target)
            or requires_mentions_identity(expr.start)
            or requires_mentions_identity(expr.body)
        )
    if isinstance(expr, ir.MapOpExpr):
        return (
            requires_mentions_identity(expr.target)
            or (expr.key is not None and requires_mentions_identity(expr.key))
            or (expr.value is not None and requires_mentions_identity(expr.value))
        )
    return False


def _missing_authentication_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} requires authentication.",
        why="No active session or token was provided.",
        fix="Login to create a session or provide a bearer token.",
        example="POST /api/login",
    )


def _token_invalid_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} cannot verify the token.",
        why="The bearer token could not be verified.",
        fix="Provide a valid bearer token.",
        example="Authorization: Bearer <token>",
    )


def _token_expired_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} requires a valid token.",
        why="The bearer token has expired.",
        fix="Login again to obtain a new token.",
        example="POST /api/login",
    )


def _session_revoked_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} requires an active session.",
        why="The session is revoked.",
        fix="Login again to create a new session.",
        example="POST /api/login",
    )


def _session_expired_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} requires an active session.",
        why="The session has expired.",
        fix="Login again to create a new session.",
        example="POST /api/login",
    )


def _insufficient_permissions_message(subject: str) -> str:
    return build_guidance_message(
        what=f"{subject} access is not permitted.",
        why="The identity does not meet the required role or permission.",
        fix="Provide an identity with the required permissions or update the requires clause.",
        example='requires has_role("admin")',
    )
