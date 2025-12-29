from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.parallel.isolation import validate_parallel_task
from namel3ss.runtime.executor.parallel.merge import ParallelMergeResult, ParallelTaskResult, merge_task_results
from namel3ss.runtime.executor.parallel.plan import build_parallel_plan
from namel3ss.runtime.executor.parallel.traces import (
    build_parallel_merged_event,
    build_parallel_started_event,
    build_parallel_task_finished_event,
)
from namel3ss.runtime.executor.signals import _ReturnSignal


def execute_parallel_block(ctx, stmt: ir.ParallelBlock, execute_statement) -> None:
    plan = build_parallel_plan(stmt)
    task_names = [task.name for task in plan.tasks]
    record_step(
        ctx,
        kind="parallel_start",
        what="parallel start",
        data={"tasks": task_names},
        line=stmt.line,
        column=stmt.column,
    )
    ctx.traces.append(build_parallel_started_event(task_names))

    base_locals = dict(ctx.locals)
    base_constants = set(ctx.constants)
    results: list[ParallelTaskResult] = []

    for task in plan.tasks:
        validate_parallel_task(ctx, task)
        record_step(
            ctx,
            kind="parallel_task_start",
            what=f"parallel task start {task.name}",
            line=task.line,
            column=task.column,
        )
        result, error = _run_task(ctx, task, execute_statement, base_locals, base_constants)
        ctx.traces.extend(result.traces)
        status = "ok" if error is None else "error"
        ctx.traces.append(build_parallel_task_finished_event(result, status=status, error=error))
        record_step(
            ctx,
            kind="parallel_task_end",
            what=f"parallel task end {task.name}",
            because="ok" if error is None else "error",
            line=task.line,
            column=task.column,
        )
        results.append(result)
        if error is not None:
            raise error

    merge = _merge_results(ctx, base_locals, base_constants, results)
    ctx.traces.append(build_parallel_merged_event(merge))
    record_step(
        ctx,
        kind="parallel_end",
        what="parallel end",
        line=stmt.line,
        column=stmt.column,
    )


def _merge_results(
    ctx,
    base_locals: dict[str, object],
    base_constants: set[str],
    results: list[ParallelTaskResult],
) -> ParallelMergeResult:
    merge = merge_task_results(base_locals=base_locals, base_constants=base_constants, results=results)
    ctx.locals = merge.locals
    ctx.constants = merge.constants
    ctx.last_value = list(merge.values)
    return merge


def _run_task(
    ctx,
    task: ir.ParallelTask,
    execute_statement,
    base_locals: dict[str, object],
    base_constants: set[str],
) -> tuple[ParallelTaskResult, Exception | None]:
    parent_locals = ctx.locals
    parent_constants = ctx.constants
    parent_traces = ctx.traces
    parent_record_changes = ctx.record_changes
    parent_pending = ctx.pending_tool_traces
    parent_last_value = ctx.last_value
    parent_tool_source = ctx.tool_call_source
    parent_parallel = getattr(ctx, "parallel_mode", False)
    parent_task = getattr(ctx, "parallel_task", None)

    ctx.locals = dict(base_locals)
    ctx.constants = set(base_constants)
    ctx.traces = []
    ctx.record_changes = []
    ctx.pending_tool_traces = []
    ctx.last_value = None
    ctx.tool_call_source = None
    ctx.parallel_mode = True
    ctx.parallel_task = task.name

    error: Exception | None = None
    try:
        for stmt in task.body:
            execute_statement(ctx, stmt)
    except _ReturnSignal as signal:
        ctx.last_value = signal.value
    except Exception as err:
        error = err

    _flush_pending_traces(ctx)
    locals_update = _local_updates(base_locals, ctx.locals)
    constants_update = set(ctx.constants) - set(base_constants)
    result = ParallelTaskResult(
        name=task.name,
        locals_update=locals_update,
        constants_update=constants_update,
        traces=list(ctx.traces),
        last_value=ctx.last_value,
        line=task.line,
        column=task.column,
    )

    if ctx.record_changes:
        error = error or Namel3ssError("Parallel tasks cannot write records", line=task.line, column=task.column)

    ctx.locals = parent_locals
    ctx.constants = parent_constants
    ctx.traces = parent_traces
    ctx.record_changes = parent_record_changes
    ctx.pending_tool_traces = parent_pending
    ctx.last_value = parent_last_value
    ctx.tool_call_source = parent_tool_source
    ctx.parallel_mode = parent_parallel
    ctx.parallel_task = parent_task

    return result, error


def _local_updates(base_locals: dict[str, object], task_locals: dict[str, object]) -> dict[str, object]:
    updates: dict[str, object] = {}
    for name, value in task_locals.items():
        if name not in base_locals or base_locals[name] != value:
            updates[name] = value
    return updates


def _flush_pending_traces(ctx) -> None:
    if not ctx.pending_tool_traces:
        return
    ctx.traces.extend(ctx.pending_tool_traces)
    ctx.pending_tool_traces = []


__all__ = ["execute_parallel_block"]
