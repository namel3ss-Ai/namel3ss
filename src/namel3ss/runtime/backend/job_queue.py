from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.runtime.backend import studio_effect_adapter
from namel3ss.runtime.backend.logical_clock import current_logical_time


@dataclass
class JobRequest:
    name: str
    payload: object


SystemJobHandler = Callable[[object, object], object]
_SYSTEM_JOBS: dict[str, SystemJobHandler] = {}


def register_system_job(name: str, handler: SystemJobHandler) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("system job name must be a non-empty string")
    if not callable(handler):
        raise ValueError("system job handler must be callable")
    _SYSTEM_JOBS[name.strip()] = handler


def initialize_job_triggers(ctx) -> None:
    if not getattr(ctx, "jobs", None):
        return
    ctx.job_trigger_state = {}
    for job_name in getattr(ctx, "job_order", []):
        job = ctx.jobs.get(job_name)
        if job is None or job.when is None:
            continue
        ctx.job_trigger_state[job_name] = _evaluate_when(ctx, job.when)


def update_job_triggers(ctx) -> None:
    if not getattr(ctx, "jobs", None):
        return
    for job_name in getattr(ctx, "job_order", []):
        job = ctx.jobs.get(job_name)
        if job is None or job.when is None:
            continue
        current = _evaluate_when(ctx, job.when)
        previous = ctx.job_trigger_state.get(job_name, False)
        ctx.job_trigger_state[job_name] = current
        if not previous and current:
            enqueue_job(ctx, job_name, {}, line=job.line, column=job.column, reason="state_change")


def enqueue_job(
    ctx,
    job_name: str,
    payload: object,
    *,
    line: int | None,
    column: int | None,
    reason: str | None = None,
    due_time: int | None = None,
    order: int | None = None,
) -> None:
    _require_jobs_capability(ctx, line=line, column=column)
    require_job(ctx, job_name, line=line, column=column)
    _enqueue_entry(
        ctx,
        job_name,
        payload,
        line=line,
        column=column,
        reason=reason,
        due_time=due_time,
        order=order,
    )


def enqueue_system_job(
    ctx,
    job_name: str,
    payload: object,
    *,
    line: int | None,
    column: int | None,
    reason: str | None = None,
    due_time: int | None = None,
    order: int | None = None,
) -> None:
    handler = _SYSTEM_JOBS.get(job_name)
    if handler is None:
        raise Namel3ssError(f"Unknown system job '{job_name}'.")
    _enqueue_entry(
        ctx,
        job_name,
        payload,
        line=line,
        column=column,
        reason=reason,
        due_time=due_time,
        order=order,
    )


def run_job_queue(ctx) -> None:
    if not getattr(ctx, "job_queue", None):
        return
    while ctx.job_queue:
        ctx.job_queue.sort(key=_job_sort_key)
        entry = ctx.job_queue.pop(0)
        job_name = entry.get("name") if isinstance(entry, dict) else None
        payload = entry.get("payload") if isinstance(entry, dict) else None
        if not isinstance(job_name, str):
            raise Namel3ssError("Job queue entry is invalid")
        job = ctx.jobs.get(job_name) if getattr(ctx, "jobs", None) else None
        if job is None:
            handler = _SYSTEM_JOBS.get(job_name)
            if handler is None:
                raise Namel3ssError(f"Unknown job '{job_name}'.")
            _run_system_job(ctx, job_name, handler, payload)
        else:
            _run_job(ctx, job, payload)
        update_job_triggers(ctx)


def _run_job(ctx, job: ir.JobDecl, payload: object) -> None:
    from namel3ss.runtime.executor.stmt.core import execute_statement

    original_locals = ctx.locals
    original_constants = ctx.constants
    original_call_stack = ctx.call_stack
    original_parallel_mode = ctx.parallel_mode
    original_parallel_task = ctx.parallel_task
    original_last_value = ctx.last_value
    original_statement = getattr(ctx, "current_statement", None)
    original_statement_index = getattr(ctx, "current_statement_index", None)
    ctx.locals = {"input": payload if payload is not None else {}, "secrets": original_locals.get("secrets", {})}
    ctx.constants = set()
    ctx.call_stack = []
    ctx.parallel_mode = False
    ctx.parallel_task = None
    ctx.last_value = None
    record_step(
        ctx,
        kind="job_start",
        what=f"job '{job.name}' started",
        line=job.line,
        column=job.column,
    )
    span_id = None
    obs = getattr(ctx, "observability", None)
    if obs:
        span_id = obs.start_span(
            ctx,
            name=f"job:{job.name}",
            kind="job",
            details={"job": job.name},
            timing_name="job",
            timing_labels={"job": job.name},
        )
    studio_effect_adapter.record_job_started(ctx, job_name=job.name, payload=payload if payload is not None else {})
    status = "ok"
    output = None
    try:
        for idx, stmt in enumerate(job.body, start=1):
            ctx.current_statement = stmt
            ctx.current_statement_index = idx
            execute_statement(ctx, stmt)
    except _ReturnSignal as signal:
        ctx.last_value = signal.value
    except Exception:
        status = "error"
        raise
    finally:
        if span_id:
            obs.end_span(ctx, span_id, status=status)
        if status == "ok":
            output = ctx.last_value
        studio_effect_adapter.record_job_finished(ctx, job_name=job.name, output=output, status=status)
        record_step(
            ctx,
            kind="job_finish",
            what=f"job '{job.name}' finished",
            line=job.line,
            column=job.column,
        )
        ctx.locals = original_locals
        ctx.constants = original_constants
        ctx.call_stack = original_call_stack
        ctx.parallel_mode = original_parallel_mode
        ctx.parallel_task = original_parallel_task
        ctx.last_value = original_last_value
        ctx.current_statement = original_statement
        ctx.current_statement_index = original_statement_index


def _run_system_job(ctx, job_name: str, handler: SystemJobHandler, payload: object) -> None:
    record_step(
        ctx,
        kind="job_start",
        what=f"job '{job_name}' started",
        line=None,
        column=None,
    )
    span_id = None
    obs = getattr(ctx, "observability", None)
    if obs:
        span_id = obs.start_span(
            ctx,
            name=f"job:{job_name}",
            kind="job",
            details={"job": job_name},
            timing_name="job",
            timing_labels={"job": job_name},
        )
    studio_effect_adapter.record_job_started(ctx, job_name=job_name, payload=payload if payload is not None else {})
    status = "ok"
    output = None
    try:
        output = handler(ctx, payload)
    except Exception:
        status = "error"
        raise
    finally:
        if span_id:
            obs.end_span(ctx, span_id, status=status)
        studio_effect_adapter.record_job_finished(ctx, job_name=job_name, output=output, status=status)
        record_step(
            ctx,
            kind="job_finish",
            what=f"job '{job_name}' finished",
            line=None,
            column=None,
        )


def _evaluate_when(ctx, expr: ir.Expression) -> bool:
    from namel3ss.runtime.executor.expr_eval import evaluate_expression

    original_locals = ctx.locals
    ctx.locals = {"input": {}, "secrets": original_locals.get("secrets", {})}
    try:
        value = evaluate_expression(ctx, expr)
    except Namel3ssError as err:
        if err.message.startswith("Unknown state path"):
            return False
        raise
    finally:
        ctx.locals = original_locals
    if not isinstance(value, bool):
        raise Namel3ssError(
            "Job when clauses must evaluate to true or false",
            line=getattr(expr, "line", None),
            column=getattr(expr, "column", None),
        )
    return value


def require_job(ctx, job_name: str, *, line: int | None, column: int | None) -> ir.JobDecl:
    job = ctx.jobs.get(job_name) if getattr(ctx, "jobs", None) else None
    if job is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown job '{job_name}'.",
                why="Jobs must be declared before they are enqueued.",
                fix="Declare the job in your app.ai file.",
                example=f'job "{job_name}":\n  return "ok"',
            ),
            line=line,
            column=column,
        )
    return job


def next_job_order(ctx) -> int:
    current = getattr(ctx, "job_enqueue_counter", 0)
    ctx.job_enqueue_counter = current + 1
    return current


def _job_sort_key(entry: dict) -> tuple[int, int, str]:
    due_time = entry.get("due_time")
    order = entry.get("order")
    job_name = entry.get("name")
    due_val = due_time if isinstance(due_time, int) else 0
    order_val = order if isinstance(order, int) else 0
    name_val = job_name if isinstance(job_name, str) else ""
    return (due_val, order_val, name_val)


def _enqueue_entry(
    ctx,
    job_name: str,
    payload: object,
    *,
    line: int | None,
    column: int | None,
    reason: str | None,
    due_time: int | None,
    order: int | None,
) -> None:
    if due_time is None:
        due_time = current_logical_time(ctx)
    if order is None:
        order = next_job_order(ctx)
    obs = getattr(ctx, "observability", None)
    span_id = None
    if obs:
        details = {"job": job_name, "due_time": int(due_time), "order": int(order)}
        if reason:
            details["reason"] = reason
        span_id = obs.start_span(
            ctx,
            name=f"job:enqueue:{job_name}",
            kind="job_enqueue",
            details=details,
        )
    try:
        ctx.job_queue.append(
            {
                "name": job_name,
                "payload": payload,
                "due_time": int(due_time),
                "order": int(order),
            }
        )
        reason_text = f" ({reason})" if reason else ""
        record_step(
            ctx,
            kind="job_enqueued",
            what=f"job '{job_name}' enqueued{reason_text}",
            line=line,
            column=column,
        )
        studio_effect_adapter.record_job_enqueued(ctx, job_name=job_name, payload=payload)
    except Exception:
        if span_id:
            obs.end_span(ctx, span_id, status="error")
        raise
    else:
        if span_id:
            obs.end_span(ctx, span_id, status="ok")


def _require_jobs_capability(ctx, *, line: int | None, column: int | None) -> None:
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if "jobs" in allowed:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Jobs capability is not enabled.",
            why="Jobs are deny-by-default and must be explicitly allowed.",
            fix="Add 'jobs' to the capabilities block in app.ai.",
            example="capabilities:\n  jobs",
        ),
        line=line,
        column=column,
    )


__all__ = [
    "JobRequest",
    "enqueue_job",
    "enqueue_system_job",
    "initialize_job_triggers",
    "next_job_order",
    "require_job",
    "register_system_job",
    "run_job_queue",
    "update_job_triggers",
]
