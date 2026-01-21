from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.explain import (
    ExpressionExplainCollector,
    build_expression_explain_trace,
    format_expression_canonical,
)
from namel3ss.runtime.execution.normalize import format_assignable
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.assign import assign
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.runtime.executor.stmt.ai_tools import (
    execute_ask_ai_stmt,
    execute_run_agent_stmt,
    execute_run_agents_parallel_stmt,
)
from namel3ss.runtime.executor.stmt.control_flow import (
    execute_for_each,
    execute_if,
    execute_match,
    execute_parallel,
    execute_repeat,
    execute_repeat_while,
)
from namel3ss.runtime.executor.stmt.records import (
    execute_create,
    execute_delete,
    execute_find,
    execute_save,
    execute_update,
)
from namel3ss.runtime.backend.job_queue import enqueue_job
from namel3ss.runtime.backend.logical_clock import require_non_negative_int
from namel3ss.runtime.backend.scheduler import advance_time, schedule_job
from namel3ss.ui.settings import UI_ALLOWED_VALUES
from namel3ss.utils.numbers import is_number


def execute_statement(ctx: ExecutionContext, stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.Let):
        _execute_let(ctx, stmt)
        return
    if isinstance(stmt, ir.Set):
        _execute_set(ctx, stmt)
        return
    if isinstance(stmt, ir.If):
        execute_if(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.Return):
        _execute_return(ctx, stmt)
        return
    if isinstance(stmt, ir.Repeat):
        execute_repeat(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.RepeatWhile):
        execute_repeat_while(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.ForEach):
        execute_for_each(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.Match):
        execute_match(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.TryCatch):
        _execute_try_catch(ctx, stmt)
        return
    if isinstance(stmt, ir.AskAIStmt):
        execute_ask_ai_stmt(ctx, stmt)
        return
    if isinstance(stmt, ir.RunAgentStmt):
        execute_run_agent_stmt(ctx, stmt)
        return
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        execute_run_agents_parallel_stmt(ctx, stmt)
        return
    if isinstance(stmt, ir.ParallelBlock):
        execute_parallel(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.Save):
        execute_save(ctx, stmt)
        return
    if isinstance(stmt, ir.Create):
        execute_create(ctx, stmt)
        return
    if isinstance(stmt, ir.Find):
        execute_find(ctx, stmt)
        return
    if isinstance(stmt, ir.Update):
        execute_update(ctx, stmt)
        return
    if isinstance(stmt, ir.Delete):
        execute_delete(ctx, stmt)
        return
    if isinstance(stmt, ir.ThemeChange):
        _execute_theme_change(ctx, stmt)
        return
    if isinstance(stmt, ir.LogStmt):
        _execute_log(ctx, stmt)
        return
    if isinstance(stmt, ir.MetricStmt):
        _execute_metric(ctx, stmt)
        return
    if isinstance(stmt, ir.EnqueueJob):
        _execute_enqueue_job(ctx, stmt)
        return
    if isinstance(stmt, ir.AdvanceTime):
        _execute_advance_time(ctx, stmt)
        return
    raise Namel3ssError(f"Unsupported statement type: {type(stmt)}", line=stmt.line, column=stmt.column)


def _execute_let(ctx: ExecutionContext, stmt: ir.Let) -> None:
    calc_info = _calc_assignment_info(ctx, stmt.line)
    collector = ExpressionExplainCollector() if calc_info else None
    value = evaluate_expression(ctx, stmt.expression, collector)
    ctx.locals[stmt.name] = value
    if stmt.constant:
        ctx.constants.add(stmt.name)
    record_step(
        ctx,
        kind="statement_let",
        what=f"set local {stmt.name}",
        line=stmt.line,
        column=stmt.column,
    )
    if collector:
        _append_expression_explain(
            ctx,
            target=stmt.name,
            expression=stmt.expression,
            value=value,
            collector=collector,
            calc_info=calc_info,
            assignment_kind="let",
            line=stmt.line,
            column=stmt.column,
        )
    ctx.last_value = value


def _execute_set(ctx: ExecutionContext, stmt: ir.Set) -> None:
    if getattr(ctx, "parallel_mode", False) and isinstance(stmt.target, ir.StatePath):
        raise Namel3ssError("Parallel tasks cannot change state", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []) and isinstance(stmt.target, ir.StatePath):
        raise Namel3ssError("Functions cannot change state", line=stmt.line, column=stmt.column)
    calc_info = _calc_assignment_info(ctx, stmt.line)
    collector = ExpressionExplainCollector() if calc_info else None
    value = evaluate_expression(ctx, stmt.expression, collector)
    assign(ctx, stmt.target, value, stmt)
    record_step(
        ctx,
        kind="statement_set",
        what=f"set {format_assignable(stmt.target)}",
        line=stmt.line,
        column=stmt.column,
    )
    if collector:
        _append_expression_explain(
            ctx,
            target=format_assignable(stmt.target),
            expression=stmt.expression,
            value=value,
            collector=collector,
            calc_info=calc_info,
            assignment_kind="set",
            line=stmt.line,
            column=stmt.column,
        )
    ctx.last_value = value


def _execute_return(ctx: ExecutionContext, stmt: ir.Return) -> None:
    value = evaluate_expression(ctx, stmt.expression)
    record_step(
        ctx,
        kind="statement_return",
        what="returned a value",
        line=stmt.line,
        column=stmt.column,
    )
    raise _ReturnSignal(value)


def _execute_try_catch(ctx: ExecutionContext, stmt: ir.TryCatch) -> None:
    record_step(
        ctx,
        kind="decision_try",
        what="try block",
        line=stmt.line,
        column=stmt.column,
    )
    try:
        for child in stmt.try_body:
            execute_statement(ctx, child)
    except Namel3ssError as err:
        record_step(
            ctx,
            kind="catch_taken",
            what="catch block taken",
            because="error raised",
            line=stmt.line,
            column=stmt.column,
        )
        ctx.locals[stmt.catch_var] = err
        for child in stmt.catch_body:
            execute_statement(ctx, child)
    else:
        record_step(
            ctx,
            kind="catch_skipped",
            what="catch block skipped",
            because="no error",
            line=stmt.line,
            column=stmt.column,
        )


def _execute_theme_change(ctx: ExecutionContext, stmt: ir.ThemeChange) -> None:
    if getattr(ctx, "parallel_mode", False):
        raise Namel3ssError("Parallel tasks cannot change theme", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot change theme", line=stmt.line, column=stmt.column)
    allowed = set(UI_ALLOWED_VALUES.get("theme", []))
    if stmt.value not in allowed:
        raise Namel3ssError(
            f"Theme must be one of: {', '.join(sorted(allowed))}",
            line=stmt.line,
            column=stmt.column,
        )
    ctx.runtime_theme = stmt.value
    ctx.traces.append({"type": "theme_change", "value": stmt.value})
    record_step(
        ctx,
        kind="statement_theme",
        what=f"set theme {stmt.value}",
        line=stmt.line,
        column=stmt.column,
    )
    ctx.last_value = stmt.value


def _execute_enqueue_job(ctx: ExecutionContext, stmt: ir.EnqueueJob) -> None:
    payload = {}
    if stmt.input_expr is not None:
        payload = evaluate_expression(ctx, stmt.input_expr)
    if stmt.schedule_kind and stmt.schedule_expr is not None:
        schedule_value = evaluate_expression(ctx, stmt.schedule_expr)
        schedule_job(
            ctx,
            stmt.job_name,
            payload,
            schedule_kind=stmt.schedule_kind,
            schedule_value=schedule_value,
            line=stmt.line,
            column=stmt.column,
        )
    else:
        enqueue_job(ctx, stmt.job_name, payload, line=stmt.line, column=stmt.column)
    ctx.last_value = payload


def _execute_advance_time(ctx: ExecutionContext, stmt: ir.AdvanceTime) -> None:
    value = evaluate_expression(ctx, stmt.amount)
    advance_time(ctx, value, line=stmt.line, column=stmt.column)


def _execute_log(ctx: ExecutionContext, stmt: ir.LogStmt) -> None:
    message = evaluate_expression(ctx, stmt.message)
    fields = evaluate_expression(ctx, stmt.fields) if stmt.fields is not None else None
    if fields is not None and not isinstance(fields, dict):
        raise Namel3ssError("Log fields must be an object", line=stmt.line, column=stmt.column)
    record_step(
        ctx,
        kind="statement_log",
        what=f"log {stmt.level}",
        line=stmt.line,
        column=stmt.column,
    )
    if ctx.observability:
        ctx.observability.record_log(level=stmt.level, message=message, fields=fields)
    ctx.last_value = message


def _execute_metric(ctx: ExecutionContext, stmt: ir.MetricStmt) -> None:
    value = evaluate_expression(ctx, stmt.value) if stmt.value is not None else None
    labels = evaluate_expression(ctx, stmt.labels) if stmt.labels is not None else None
    if labels is not None and not isinstance(labels, dict):
        raise Namel3ssError("Metric labels must be an object", line=stmt.line, column=stmt.column)
    record_step(
        ctx,
        kind="statement_metric",
        what=f"metric {stmt.kind} {stmt.operation}",
        line=stmt.line,
        column=stmt.column,
    )
    if not ctx.observability:
        ctx.last_value = value
        return
    if stmt.kind == "counter":
        if stmt.operation == "increment":
            delta = 1 if value is None else value
            _require_metric_number(delta, stmt)
            ctx.observability.metrics.increment(stmt.name, value=delta, labels=labels)
        elif stmt.operation == "add":
            _require_metric_number(value, stmt)
            ctx.observability.metrics.add(stmt.name, value=value, labels=labels)
        elif stmt.operation == "set":
            _require_metric_number(value, stmt)
            ctx.observability.metrics.set(stmt.name, value=value, labels=labels)
        else:
            raise Namel3ssError("Unknown counter metric operation", line=stmt.line, column=stmt.column)
    elif stmt.kind == "timing":
        if stmt.operation != "record":
            raise Namel3ssError("Unknown timing metric operation", line=stmt.line, column=stmt.column)
        duration = require_non_negative_int(value, line=stmt.line, column=stmt.column)
        ctx.observability.metrics.record_timing(stmt.name, duration=duration, labels=labels)
    else:
        raise Namel3ssError("Unknown metric kind", line=stmt.line, column=stmt.column)
    ctx.last_value = value


def _require_metric_number(value: object, stmt: ir.MetricStmt) -> None:
    if not is_number(value):
        raise Namel3ssError("Metric value must be a number", line=stmt.line, column=stmt.column)


def _calc_assignment_info(ctx: ExecutionContext, line: int | None) -> dict[str, int] | None:
    if line is None:
        return None
    index = getattr(ctx, "calc_assignment_index", None)
    if not isinstance(index, dict) or not index:
        return None
    info = index.get(line)
    if not isinstance(info, dict):
        return None
    return info


def _append_expression_explain(
    ctx: ExecutionContext,
    *,
    target: str,
    expression: ir.Expression,
    value: object,
    collector: ExpressionExplainCollector,
    calc_info: dict[str, int] | None,
    assignment_kind: str,
    line: int | None,
    column: int | None,
) -> None:
    if not calc_info:
        return
    line_start = line or 1
    column_start = column or 1
    line_end = calc_info.get("line_end", line_start)
    column_end = calc_info.get("column_end", column_start)
    span = {
        "line_start": line_start,
        "column_start": column_start,
        "line_end": line_end,
        "column_end": column_end,
    }
    trace = build_expression_explain_trace(
        target=target,
        expression=format_expression_canonical(expression),
        result=value,
        steps=collector.steps,
        span=span,
        assignment_kind=assignment_kind,
        flow_name=getattr(ctx.flow, "name", None),
        sample_limit=collector.sample_limit,
        truncated=collector.truncated,
    )
    ctx.traces.append(trace)


__all__ = ["execute_statement"]
