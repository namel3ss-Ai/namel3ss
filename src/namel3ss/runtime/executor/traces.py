from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.execution.recorder import record_step


def _record_flow_end(ctx: ExecutionContext, *, ok: bool) -> None:
    record_step(
        ctx,
        kind="flow_end",
        what=f'flow "{ctx.flow.name}" ended',
        because="completed successfully" if ok else "ended with error",
        line=ctx.flow.line,
        column=ctx.flow.column,
    )


def _record_error_step(ctx: ExecutionContext, error: Exception) -> None:
    line = getattr(error, "line", None)
    column = getattr(error, "column", None)
    if isinstance(error, Namel3ssError):
        line = error.line
        column = error.column
    record_step(
        ctx,
        kind="error",
        what=f"error {error.__class__.__name__}",
        because=str(error),
        line=line,
        column=column,
    )


def _trace_summaries(traces: list) -> list[dict]:
    summaries: list[dict] = []
    for trace in traces:
        summaries.append(
            {
                "ai_name": getattr(trace, "ai_name", None),
                "events": len(getattr(trace, "canonical_events", []) or []),
                "tool_calls": len(getattr(trace, "tool_calls", []) or []),
            }
        )
    return summaries


def _dict_traces(traces: list) -> list[dict]:
    return [trace for trace in traces if isinstance(trace, dict)]


__all__ = ["_dict_traces", "_record_error_step", "_record_flow_end", "_trace_summaries"]
