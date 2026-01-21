from __future__ import annotations

from namel3ss.observe import summarize_value
from namel3ss.secrets import collect_secret_values


def record_job_scheduled(
    ctx,
    *,
    job_name: str,
    payload: object,
    due_time: int,
    schedule_kind: str,
) -> None:
    secret_values = collect_secret_values(ctx.config)
    event = {
        "type": "job_scheduled",
        "title": f"Job scheduled: {job_name}",
        "job": job_name,
        "schedule_kind": schedule_kind,
        "due_time": due_time,
        "input": summarize_value(payload, secret_values=secret_values),
    }
    ctx.traces.append(event)


def record_logical_time_advanced(ctx, *, previous: int, current: int, delta: int) -> None:
    event = {
        "type": "logical_time_advanced",
        "title": "Logical time advanced",
        "from": previous,
        "to": current,
        "delta": delta,
    }
    ctx.traces.append(event)


__all__ = ["record_job_scheduled", "record_logical_time_advanced"]
