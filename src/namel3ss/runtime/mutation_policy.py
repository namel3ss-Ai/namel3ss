from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.validation import ValidationMode, add_warning


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


def audit_required_enabled() -> bool:
    return os.getenv("N3_AUDIT_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}


def flow_mutates(flow: ir.Flow) -> bool:
    if getattr(flow, "declarative", False):
        return steps_mutate(getattr(flow, "steps", None) or [])
    return statements_mutate(flow.body)


def steps_mutate(steps: Iterable[ir.FlowStep]) -> bool:
    for step in steps:
        if isinstance(step, (ir.FlowCreate, ir.FlowUpdate, ir.FlowDelete)):
            return True
    return False


def statements_mutate(stmts: Iterable[ir.Statement]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, (ir.Save, ir.Create, ir.Update, ir.Delete)):
            return True
        if isinstance(stmt, ir.If):
            if statements_mutate(stmt.then_body) or statements_mutate(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if statements_mutate(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if statements_mutate(stmt.body):
                return True
        if isinstance(stmt, ir.TryCatch):
            if statements_mutate(stmt.try_body) or statements_mutate(stmt.catch_body):
                return True
        if isinstance(stmt, ir.Match):
            if any(statements_mutate(case.body) for case in stmt.cases):
                return True
            if stmt.otherwise and statements_mutate(stmt.otherwise):
                return True
    return False


def page_has_form(page: ir.Page) -> bool:
    return _page_items_have_form(page.items)


def _page_items_have_form(items: Iterable[ir.PageItem]) -> bool:
    for item in items:
        if isinstance(item, ir.FormItem):
            return True
        if hasattr(item, "children"):
            children = getattr(item, "children") or []
            if _page_items_have_form(children):
                return True
    return False


def append_mutation_policy_warnings(
    program: ir.Program,
    *,
    warnings: list | None,
    mode: ValidationMode,
) -> None:
    if warnings is None or mode != ValidationMode.STATIC:
        return
    mutating_flows = [flow for flow in program.flows if flow_mutates(flow)]
    for flow in sorted(mutating_flows, key=lambda item: item.name):
        if flow.requires is None:
            add_warning(
                warnings,
                code="requires.missing",
                message=f'Flow "{flow.name}" mutates data without requires.',
                fix="Add a requires clause to the flow header.",
                line=flow.line,
                column=flow.column,
                enforced_at="runtime",
            )
        if audit_required_enabled() and not getattr(flow, "audited", False):
            add_warning(
                warnings,
                code="audit.required",
                message=f'Flow "{flow.name}" mutates data without audited.',
                fix="Add audited to the flow header or disable audit-required mode.",
                line=flow.line,
                column=flow.column,
                enforced_at="runtime",
                category="policy",
            )
    pages_with_forms = [page for page in program.pages if page_has_form(page)]
    for page in sorted(pages_with_forms, key=lambda item: item.name):
        if page.requires is None:
            add_warning(
                warnings,
                code="requires.missing",
                message=f'Page "{page.name}" has a form without requires.',
                fix="Add a requires clause to the page header.",
                line=page.line,
                column=page.column,
                enforced_at="runtime",
            )


def evaluate_mutation_policy(
    ctx,
    *,
    action: str,
    record: str,
    line: int | None = None,
    column: int | None = None,
) -> MutationDecision:
    flow = getattr(ctx, "flow", None)
    flow_name = getattr(flow, "name", "flow")
    subject = f'flow "{flow_name}"'
    requires_expr = getattr(flow, "requires", None) if flow else None
    audited = bool(getattr(flow, "audited", False)) if flow else False
    return evaluate_mutation_policy_for_rule(
        ctx,
        action=action,
        record=record,
        subject=subject,
        requires_expr=requires_expr,
        audited=audited,
    )


def evaluate_mutation_policy_for_rule(
    ctx,
    *,
    action: str,
    record: str,
    subject: str,
    requires_expr: ir.Expression | None,
    audited: bool,
) -> MutationDecision:
    if requires_expr is None:
        return _missing_requires(subject)
    if audit_required_enabled() and not audited:
        return _audit_required(subject)
    try:
        result = _evaluate_requires(ctx, requires_expr, action=action, record=record)
    except Namel3ssError as err:
        return _policy_invalid(subject, err)
    if not isinstance(result, bool):
        return _requires_not_boolean(subject, result)
    if not result:
        return _access_denied(subject)
    return MutationDecision.allow()


def _evaluate_requires(ctx, expr: ir.Expression, *, action: str, record: str) -> object:
    locals_snapshot = getattr(ctx, "locals", {})
    locals_value = dict(locals_snapshot) if isinstance(locals_snapshot, dict) else {}
    locals_value["mutation"] = {"action": action, "record": record}
    setattr(ctx, "locals", locals_value)
    try:
        return evaluate_expression(ctx, expr)
    finally:
        setattr(ctx, "locals", locals_snapshot)


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


__all__ = [
    "MutationDecision",
    "append_mutation_policy_warnings",
    "audit_required_enabled",
    "evaluate_mutation_policy",
    "evaluate_mutation_policy_for_rule",
    "flow_mutates",
    "page_has_form",
    "requires_mentions_mutation",
    "statements_mutate",
]
