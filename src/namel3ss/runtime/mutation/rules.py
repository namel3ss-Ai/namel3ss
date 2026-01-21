from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.identity.guards import requires_mentions_identity


@dataclass(frozen=True)
class MutationDecision:
    allowed: bool
    reason_code: str | None = None
    message: str | None = None
    fix_hint: str | None = None
    error_message: str | None = None

    @classmethod
    def allow(cls) -> "MutationDecision":
        return cls(allowed=True)

    @classmethod
    def block(
        cls,
        *,
        reason_code: str,
        message: str,
        fix_hint: str,
        error_message: str | None = None,
    ) -> "MutationDecision":
        return cls(
            allowed=False,
            reason_code=reason_code,
            message=message,
            fix_hint=fix_hint,
            error_message=error_message,
        )


def _missing_requires(subject: str) -> MutationDecision:
    message = f"{subject} is missing a requires rule for mutations."
    fix = "Add a requires clause to the page or flow header."
    error_message = build_guidance_message(
        what="Mutation blocked by access control.",
        why="Mutating flows and forms must declare a requires rule.",
        fix=fix,
        example='flow "update_order": requires identity.role is "admin"',
    )
    return MutationDecision.block(
        reason_code="policy_missing",
        message=message,
        fix_hint=fix,
        error_message=error_message,
    )


def _audit_required(subject: str) -> MutationDecision:
    message = f"{subject} is missing audited while audit-required is enabled."
    fix = "Mark the mutation as audited or disable audit-required mode."
    error_message = build_guidance_message(
        what="Mutation blocked by audit policy.",
        why="Audit-required mode enforces audited mutations.",
        fix=fix,
        example='flow "update_order": audited',
    )
    return MutationDecision.block(
        reason_code="audit_required",
        message=message,
        fix_hint=fix,
        error_message=error_message,
    )


def _access_denied(subject: str) -> MutationDecision:
    fix = "Provide an identity that satisfies the requirement or update the requires rule."
    error_message = build_guidance_message(
        what=f"{subject} access is not permitted.",
        why="The requires condition evaluated to false.",
        fix=fix,
        example='requires identity.role is "admin"',
    )
    return MutationDecision.block(
        reason_code="access_denied",
        message=f"{subject} access is not permitted.",
        fix_hint=fix,
        error_message=error_message,
    )


def _auth_denied(subject: str, requires_expr: ir.Expression | None, ctx) -> MutationDecision | None:
    if not requires_mentions_identity(requires_expr):
        return None
    auth_ctx = getattr(ctx, "auth_context", None)
    auth_error = getattr(auth_ctx, "error", None) if auth_ctx is not None else None
    authenticated = bool(getattr(auth_ctx, "authenticated", False)) if auth_ctx is not None else False
    if auth_error == "missing_authentication":
        return _missing_authentication(subject)
    if auth_error == "token_invalid":
        return _token_invalid(subject)
    if auth_error == "token_expired":
        return _token_expired(subject)
    if auth_error == "session_invalid":
        return _session_revoked(subject)
    if auth_error == "session_revoked":
        return _session_revoked(subject)
    if auth_error == "session_expired":
        return _session_expired(subject)
    if authenticated:
        return _insufficient_permissions(subject)
    return None


def _missing_authentication(subject: str) -> MutationDecision:
    fix = "Login to create a session or provide a bearer token."
    error_message = build_guidance_message(
        what=f"{subject} requires authentication.",
        why="No active session or token was provided.",
        fix=fix,
        example="POST /api/login",
    )
    return MutationDecision.block(
        reason_code="missing_authentication",
        message=f"{subject} requires authentication.",
        fix_hint=fix,
        error_message=error_message,
    )


def _token_invalid(subject: str) -> MutationDecision:
    fix = "Provide a valid bearer token."
    error_message = build_guidance_message(
        what=f"{subject} cannot verify the token.",
        why="The bearer token could not be verified.",
        fix=fix,
        example="Authorization: Bearer <token>",
    )
    return MutationDecision.block(
        reason_code="token_invalid",
        message=f"{subject} cannot verify the token.",
        fix_hint=fix,
        error_message=error_message,
    )


def _token_expired(subject: str) -> MutationDecision:
    fix = "Login again to obtain a new token."
    error_message = build_guidance_message(
        what=f"{subject} requires a valid token.",
        why="The bearer token has expired.",
        fix=fix,
        example="POST /api/login",
    )
    return MutationDecision.block(
        reason_code="token_expired",
        message=f"{subject} requires a valid token.",
        fix_hint=fix,
        error_message=error_message,
    )


def _session_revoked(subject: str) -> MutationDecision:
    fix = "Login again to create a new session."
    error_message = build_guidance_message(
        what=f"{subject} requires an active session.",
        why="The session is revoked.",
        fix=fix,
        example="POST /api/login",
    )
    return MutationDecision.block(
        reason_code="session_revoked",
        message=f"{subject} requires an active session.",
        fix_hint=fix,
        error_message=error_message,
    )


def _session_expired(subject: str) -> MutationDecision:
    fix = "Login again to create a new session."
    error_message = build_guidance_message(
        what=f"{subject} requires an active session.",
        why="The session has expired.",
        fix=fix,
        example="POST /api/login",
    )
    return MutationDecision.block(
        reason_code="session_expired",
        message=f"{subject} requires an active session.",
        fix_hint=fix,
        error_message=error_message,
    )


def _insufficient_permissions(subject: str) -> MutationDecision:
    fix = "Provide an identity with the required permissions or update the requires clause."
    error_message = build_guidance_message(
        what=f"{subject} access is not permitted.",
        why="The identity does not meet the required role or permission.",
        fix=fix,
        example='requires has_role("admin")',
    )
    return MutationDecision.block(
        reason_code="insufficient_permissions",
        message=f"{subject} access is not permitted.",
        fix_hint=fix,
        error_message=error_message,
    )


def _requires_not_boolean(subject: str, value: object) -> MutationDecision:
    kind = _value_kind(value)
    fix = "Use a comparison so the requires clause evaluates to true or false."
    error_message = build_guidance_message(
        what=f"{subject} requires a boolean condition.",
        why=f"The requires expression evaluated to {kind}, not true or false.",
        fix=fix,
        example='requires identity.role is "admin"',
    )
    return MutationDecision.block(
        reason_code="policy_invalid",
        message=f"{subject} requires a boolean condition.",
        fix_hint=fix,
        error_message=error_message,
    )


def _policy_invalid(subject: str, err: Namel3ssError) -> MutationDecision:
    parsed = _parse_guidance_message(err.message)
    message = parsed.get("what") or _first_line(err.message) or f"{subject} requires a valid access rule."
    fix = parsed.get("fix") or "Fix the requires clause so it can be evaluated."
    return MutationDecision.block(
        reason_code="policy_invalid",
        message=message,
        fix_hint=fix,
        error_message=err.message,
    )


def _first_line(message: str | None) -> str | None:
    if not message:
        return None
    return message.splitlines()[0].strip() or None


def _parse_guidance_message(message: str | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not message:
        return parsed
    for raw_line in str(message).splitlines():
        line = raw_line.strip()
        if line.startswith("What happened:"):
            parsed["what"] = line[len("What happened:") :].strip()
        elif line.startswith("Why:"):
            parsed["why"] = line[len("Why:") :].strip()
        elif line.startswith("Fix:"):
            parsed["fix"] = line[len("Fix:") :].strip()
        elif line.startswith("Example:"):
            parsed["example"] = line[len("Example:") :].strip()
    return parsed


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


def requires_mentions_mutation(expr: ir.Expression | None) -> bool:
    if expr is None:
        return False
    if isinstance(expr, ir.VarReference):
        return expr.name == "mutation"
    if isinstance(expr, ir.AttrAccess):
        return expr.base == "mutation"
    if isinstance(expr, ir.UnaryOp):
        return requires_mentions_mutation(expr.operand)
    if isinstance(expr, ir.BinaryOp):
        return requires_mentions_mutation(expr.left) or requires_mentions_mutation(expr.right)
    if isinstance(expr, ir.Comparison):
        return requires_mentions_mutation(expr.left) or requires_mentions_mutation(expr.right)
    if isinstance(expr, ir.ToolCallExpr):
        return any(requires_mentions_mutation(arg.value) for arg in expr.arguments)
    if isinstance(expr, ir.ListExpr):
        return any(requires_mentions_mutation(item) for item in expr.items)
    if isinstance(expr, ir.MapExpr):
        return any(
            requires_mentions_mutation(entry.key) or requires_mentions_mutation(entry.value)
            for entry in expr.entries
        )
    if isinstance(expr, ir.ListOpExpr):
        return (
            requires_mentions_mutation(expr.target)
            or (expr.value is not None and requires_mentions_mutation(expr.value))
            or (expr.index is not None and requires_mentions_mutation(expr.index))
        )
    if isinstance(expr, ir.ListMapExpr):
        return requires_mentions_mutation(expr.target) or requires_mentions_mutation(expr.body)
    if isinstance(expr, ir.ListFilterExpr):
        return requires_mentions_mutation(expr.target) or requires_mentions_mutation(expr.predicate)
    if isinstance(expr, ir.ListReduceExpr):
        return (
            requires_mentions_mutation(expr.target)
            or requires_mentions_mutation(expr.start)
            or requires_mentions_mutation(expr.body)
        )
    if isinstance(expr, ir.MapOpExpr):
        return (
            requires_mentions_mutation(expr.target)
            or (expr.key is not None and requires_mentions_mutation(expr.key))
            or (expr.value is not None and requires_mentions_mutation(expr.value))
        )
    return False


__all__ = ["MutationDecision", "requires_mentions_mutation"]
