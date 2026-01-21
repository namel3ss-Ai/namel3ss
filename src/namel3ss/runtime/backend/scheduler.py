from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.backend.job_queue import enqueue_job, next_job_order, require_job
from namel3ss.runtime.backend.logical_clock import advance_logical_time, current_logical_time, require_non_negative_int
from namel3ss.runtime.backend.studio_effect_adapter_jobs import (
    record_job_scheduled,
    record_logical_time_advanced,
)
from namel3ss.runtime.execution.recorder import record_step


def schedule_job(
    ctx,
    job_name: str,
    payload: object,
    *,
    schedule_kind: str,
    schedule_value: object,
    line: int | None,
    column: int | None,
) -> None:
    _require_jobs_capability(ctx, line=line, column=column)
    _require_scheduling_capability(ctx, line=line, column=column)
    require_job(ctx, job_name, line=line, column=column)
    due_time = _resolve_due_time(ctx, schedule_kind, schedule_value, line=line, column=column)
    order = next_job_order(ctx)
    entry = {
        "name": job_name,
        "payload": payload,
        "due_time": due_time,
        "order": order,
        "line": line,
        "column": column,
    }
    ctx.scheduled_jobs.append(entry)
    record_step(
        ctx,
        kind="job_scheduled",
        what=f"job '{job_name}' scheduled for {due_time}",
        line=line,
        column=column,
    )
    record_job_scheduled(
        ctx,
        job_name=job_name,
        payload=payload,
        due_time=due_time,
        schedule_kind=schedule_kind,
    )


def advance_time(ctx, amount: object, *, line: int | None, column: int | None) -> None:
    _require_scheduling_capability(ctx, line=line, column=column)
    before, after = advance_logical_time(ctx, amount, line=line, column=column)
    record_step(
        ctx,
        kind="logical_time_advanced",
        what=f"logical time advanced to {after}",
        line=line,
        column=column,
    )
    record_logical_time_advanced(ctx, previous=before, current=after, delta=after - before)
    _release_due_jobs(ctx, line=line, column=column)


def _resolve_due_time(
    ctx,
    schedule_kind: str,
    schedule_value: object,
    *,
    line: int | None,
    column: int | None,
) -> int:
    now = current_logical_time(ctx)
    if schedule_kind == "after":
        delta = require_non_negative_int(schedule_value, line=line, column=column)
        return now + delta
    if schedule_kind == "at":
        due_time = require_non_negative_int(schedule_value, line=line, column=column)
        if due_time < now:
            raise Namel3ssError(
                build_guidance_message(
                    what="Scheduled time is already in the past.",
                    why="Jobs can only be scheduled at or after the current logical time.",
                    fix="Advance logical time or choose a later value.",
                    example="enqueue job \"refresh\" at 5",
                ),
                line=line,
                column=column,
            )
        return due_time
    raise Namel3ssError(
        build_guidance_message(
            what="Unknown schedule kind.",
            why="Jobs can be scheduled using after or at.",
            fix="Use after <duration> or at <time>.",
            example="enqueue job \"refresh\" after 2",
        ),
        line=line,
        column=column,
    )


def _release_due_jobs(ctx, *, line: int | None, column: int | None) -> None:
    scheduled = getattr(ctx, "scheduled_jobs", None)
    if not scheduled:
        return
    current = current_logical_time(ctx)
    due: list[dict] = []
    pending: list[dict] = []
    for entry in scheduled:
        due_time = entry.get("due_time") if isinstance(entry, dict) else None
        if isinstance(due_time, int) and due_time <= current:
            due.append(entry)
        else:
            pending.append(entry)
    ctx.scheduled_jobs = pending
    for entry in sorted(due, key=_scheduled_sort_key):
        enqueue_job(
            ctx,
            entry.get("name"),
            entry.get("payload"),
            line=entry.get("line", line),
            column=entry.get("column", column),
            reason="scheduled",
            due_time=entry.get("due_time"),
            order=entry.get("order"),
        )


def _scheduled_sort_key(entry: dict) -> tuple[int, int, str]:
    due_time = entry.get("due_time")
    order = entry.get("order")
    job_name = entry.get("name")
    due_val = due_time if isinstance(due_time, int) else 0
    order_val = order if isinstance(order, int) else 0
    name_val = job_name if isinstance(job_name, str) else ""
    return (due_val, order_val, name_val)


def _require_scheduling_capability(ctx, *, line: int | None, column: int | None) -> None:
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if "scheduling" in allowed:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Scheduling capability is not enabled.",
            why="Scheduling is deny-by-default and must be explicitly allowed.",
            fix="Add 'scheduling' to the capabilities block in app.ai.",
            example="capabilities:\n  scheduling",
        ),
        line=line,
        column=column,
    )


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


__all__ = ["advance_time", "schedule_job"]
