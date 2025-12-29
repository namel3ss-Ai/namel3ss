from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_parallel_started(*, title: str, lines: list[str]) -> dict:
    return {
        "type": TraceEventType.PARALLEL_STARTED,
        "trace_version": TRACE_VERSION,
        "title": title,
        "lines": list(lines),
    }


def build_parallel_task_finished(*, task_name: str, status: str, title: str, lines: list[str]) -> dict:
    return {
        "type": TraceEventType.PARALLEL_TASK_FINISHED,
        "trace_version": TRACE_VERSION,
        "task_name": task_name,
        "status": status,
        "title": title,
        "lines": list(lines),
    }


def build_parallel_merged(*, title: str, lines: list[str]) -> dict:
    return {
        "type": TraceEventType.PARALLEL_MERGED,
        "trace_version": TRACE_VERSION,
        "title": title,
        "lines": list(lines),
    }


__all__ = [
    "build_parallel_merged",
    "build_parallel_started",
    "build_parallel_task_finished",
]
