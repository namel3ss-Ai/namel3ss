from __future__ import annotations

import os
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.validation import ValidationMode, add_warning

from namel3ss.runtime.mutation.rules import (
    MutationDecision,
    _access_denied,
    _audit_required,
    _auth_denied,
    _missing_requires,
    _policy_invalid,
    _requires_not_boolean,
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
        auth_decision = _auth_denied(subject, requires_expr, ctx)
        if auth_decision is not None:
            return auth_decision
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


__all__ = [
    "MutationDecision",
    "append_mutation_policy_warnings",
    "audit_required_enabled",
    "evaluate_mutation_policy",
    "evaluate_mutation_policy_for_rule",
    "flow_mutates",
    "page_has_form",
    "statements_mutate",
    "steps_mutate",
]
