from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir


@dataclass(frozen=True)
class AsyncHandle:
    task_id: str
    name: str


@dataclass
class AsyncTask:
    id: str
    name: str
    status: str
    result: object | None
    error: Exception | None
    line: int | None
    column: int | None
    start_order: int


def launch_async_call(ctx, *, name: str, expression: ir.Expression, line: int | None, column: int | None) -> AsyncHandle:
    _validate_launch_expression(expression, line=line, column=column)
    start_order = int(getattr(ctx, "async_launch_counter", 0)) + 1
    ctx.async_launch_counter = start_order
    task_id = f"{ctx.flow.name}:{start_order:04d}:{name}"
    task = AsyncTask(
        id=task_id,
        name=name,
        status="pending",
        result=None,
        error=None,
        line=line,
        column=column,
        start_order=start_order,
    )
    ctx.async_tasks[task_id] = task

    locals_snapshot = _snapshot_locals(ctx, line=line, column=column)
    state_snapshot = copy.deepcopy(ctx.state)
    constants_snapshot = set(ctx.constants)

    parent_locals = ctx.locals
    parent_state = ctx.state
    parent_constants = ctx.constants
    parent_parallel_mode = getattr(ctx, "parallel_mode", False)
    parent_parallel_task = getattr(ctx, "parallel_task", None)
    parent_tool_source = getattr(ctx, "tool_call_source", None)
    task.status = "running"
    try:
        from namel3ss.runtime.executor.expr_eval import evaluate_expression

        ctx.locals = locals_snapshot
        ctx.state = state_snapshot
        ctx.constants = constants_snapshot
        ctx.parallel_mode = False
        ctx.parallel_task = None
        ctx.tool_call_source = f"async:{name}"
        task.result = evaluate_expression(ctx, expression)
        task.status = "completed"
    except Exception as err:  # pragma: no cover - defensive
        task.error = err
        task.status = "failed"
    finally:
        ctx.locals = parent_locals
        ctx.state = parent_state
        ctx.constants = parent_constants
        ctx.parallel_mode = parent_parallel_mode
        ctx.parallel_task = parent_parallel_task
        ctx.tool_call_source = parent_tool_source
    return AsyncHandle(task_id=task_id, name=name)


def await_async_handle(ctx, handle: AsyncHandle, *, line: int | None, column: int | None) -> object:
    task = _require_task(ctx, handle, line=line, column=column)
    if task.status == "failed":
        if task.error is not None:
            raise task.error
        raise Namel3ssError("Async task failed", line=line, column=column)
    if task.status != "completed":
        # Tasks are launched deterministically and resolved in declaration order.
        task.status = "completed"
    return task.result


def is_async_handle(value: object) -> bool:
    return isinstance(value, AsyncHandle)


def _require_task(ctx, handle: AsyncHandle, *, line: int | None, column: int | None) -> AsyncTask:
    task = ctx.async_tasks.get(handle.task_id)
    if isinstance(task, AsyncTask):
        return task
    raise Namel3ssError(
        f'Unknown async task "{handle.name}". Launch it before await.',
        line=line,
        column=column,
    )


def _snapshot_locals(ctx, *, line: int | None, column: int | None) -> dict[str, object]:
    snapshot: dict[str, object] = {}
    for key in sorted((ctx.locals or {}).keys()):
        snapshot[key] = _materialize_value(ctx, ctx.locals[key], line=line, column=column)
    return snapshot


def _materialize_value(ctx, value: object, *, line: int | None, column: int | None) -> object:
    if isinstance(value, AsyncHandle):
        return await_async_handle(ctx, value, line=line, column=column)
    if isinstance(value, list):
        return [_materialize_value(ctx, item, line=line, column=column) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _materialize_value(ctx, item, line=line, column=column)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return copy.deepcopy(value)


def _validate_launch_expression(expression: ir.Expression, *, line: int | None, column: int | None) -> None:
    if isinstance(expression, (ir.ToolCallExpr, ir.CallFunctionExpr, ir.CallFlowExpr, ir.CallPipelineExpr)):
        return
    raise Namel3ssError(
        "async can only launch calls (tool, function, flow, or pipeline).",
        line=line,
        column=column,
    )


__all__ = ["AsyncHandle", "AsyncTask", "await_async_handle", "is_async_handle", "launch_async_call"]
