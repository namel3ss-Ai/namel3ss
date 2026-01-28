from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.observability.scrub import scrub_text
from namel3ss.runtime.execution.normalize import summarize_value
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.orchestration.merge import (
    OrchestrationBranchResult,
    merge_branch_results,
)
from namel3ss.runtime.executor.orchestration.traces import (
    build_orchestration_branch_finished_event,
    build_orchestration_branch_started_event,
    build_orchestration_merge_finished_event,
    build_orchestration_merge_started_event,
)
from namel3ss.secrets import collect_secret_values, redact_text
from namel3ss.utils.slugify import slugify_text


def execute_orchestration_block(ctx, stmt: ir.OrchestrationBlock, evaluate_expression) -> None:
    orchestration_id = _next_orchestration_id(ctx)
    branch_names = [branch.name for branch in stmt.branches]
    record_step(
        ctx,
        kind="orchestration_start",
        what="orchestration start",
        data={"orchestration_id": orchestration_id, "branches": list(branch_names)},
        line=stmt.line,
        column=stmt.column,
    )
    branch_results: list[OrchestrationBranchResult] = []
    for idx, branch in enumerate(stmt.branches, start=1):
        branch_id = _branch_id(ctx.flow.name, orchestration_id, branch.name, idx)
        call_kind, call_target = _branch_call_info(branch.call_expr)
        record_step(
            ctx,
            kind="orchestration_branch_start",
            what=f"orchestration branch {branch.name} start",
            data={
                "orchestration_id": orchestration_id,
                "branch_id": branch_id,
                "branch_name": branch.name,
                "call_kind": call_kind,
                "call_target": call_target,
            },
            line=branch.line,
            column=branch.column,
        )
        ctx.traces.append(
            build_orchestration_branch_started_event(
                branch_name=branch.name,
                branch_id=branch_id,
                call_kind=call_kind,
                call_target=call_target,
            )
        )
        status = "ok"
        value = None
        error_type = None
        error_message = None
        try:
            value = evaluate_expression(ctx, branch.call_expr)
        except Exception as err:
            status = "error"
            error_type = type(err).__name__
            error_message = _safe_error_message(ctx, err)
        branch_results.append(
            OrchestrationBranchResult(
                name=branch.name,
                status=status,
                value=value,
                error_type=error_type,
                error_message=error_message,
            )
        )
        ctx.traces.append(
            build_orchestration_branch_finished_event(
                branch_id=branch_id,
                result=branch_results[-1],
                summary=_safe_summary(value),
            )
        )
        record_step(
            ctx,
            kind="orchestration_branch_end",
            what=f"orchestration branch {branch.name} end",
            because=status,
            data={
                "orchestration_id": orchestration_id,
                "branch_id": branch_id,
                "branch_name": branch.name,
                "status": status,
            },
            line=branch.line,
            column=branch.column,
        )
    merge_id = _merge_id(ctx.flow.name, orchestration_id)
    record_step(
        ctx,
        kind="orchestration_merge_start",
        what="orchestration merge start",
        data={
            "orchestration_id": orchestration_id,
            "merge_id": merge_id,
            "policy": stmt.merge.policy,
        },
        line=stmt.merge.line or stmt.line,
        column=stmt.merge.column or stmt.column,
    )
    ctx.traces.append(
        build_orchestration_merge_started_event(
            merge_id=merge_id,
            policy=stmt.merge.policy,
            branches=branch_results,
        )
    )
    outcome, error_message = merge_branch_results(
        policy=stmt.merge.policy,
        branches=branch_results,
        precedence=stmt.merge.precedence,
    )
    ctx.traces.append(
        build_orchestration_merge_finished_event(
            merge_id=merge_id,
            outcome=outcome,
        )
    )
    record_step(
        ctx,
        kind="orchestration_merge_end",
        what="orchestration merge end",
        because=outcome.status,
        data={
            "orchestration_id": orchestration_id,
            "merge_id": merge_id,
            "policy": outcome.policy,
            "status": outcome.status,
            "selected": outcome.selected,
        },
        line=stmt.merge.line or stmt.line,
        column=stmt.merge.column or stmt.column,
    )
    if error_message:
        raise Namel3ssError(
            error_message,
            line=stmt.merge.line or stmt.line,
            column=stmt.merge.column or stmt.column,
        )
    ctx.locals[stmt.target] = outcome.output
    ctx.last_value = outcome.output


def _branch_call_info(expr: ir.Expression) -> tuple[str, str]:
    if isinstance(expr, ir.CallFlowExpr):
        return "flow", expr.flow_name
    if isinstance(expr, ir.CallPipelineExpr):
        return "pipeline", expr.pipeline_name
    return "expression", "unknown"


def _next_orchestration_id(ctx) -> int:
    counter = getattr(ctx, "orchestration_counter", 0) + 1
    setattr(ctx, "orchestration_counter", counter)
    return counter


def _branch_id(flow_name: str, orchestration_id: int, branch_name: str, ordinal: int) -> str:
    slug = slugify_text(branch_name) or "branch"
    return f"branch:{flow_name}:{orchestration_id}:{slug}:{ordinal}"


def _merge_id(flow_name: str, orchestration_id: int) -> str:
    return f"merge:{flow_name}:{orchestration_id}"


def _safe_summary(value: object) -> str:
    if isinstance(value, str):
        return f"text length {len(value)}"
    return summarize_value(value)


def _safe_error_message(ctx, error: Exception) -> str:
    secret_values = collect_secret_values(getattr(ctx, "config", None))
    text = redact_text(str(error), secret_values)
    text = scrub_text(text, project_root=getattr(ctx, "project_root", None), app_path=getattr(ctx, "app_path", None))
    return text


__all__ = ["execute_orchestration_block"]
