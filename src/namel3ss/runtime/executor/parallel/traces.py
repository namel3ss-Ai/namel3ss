from __future__ import annotations

from namel3ss.runtime.executor.parallel.merge import ParallelMergeResult, ParallelTaskResult
from namel3ss.traces.builders import (
    build_parallel_merged,
    build_parallel_started,
    build_parallel_task_finished,
)


_BRACKET_CHARS = str.maketrans({")": " ", "(": " ", "]": " ", "[": " ", "}": " ", "{": " "})


def build_parallel_started_event(task_names: list[str]) -> dict:
    return build_parallel_started(
        title="Parallel started",
        lines=[_sanitize(name) for name in task_names],
    )


def build_parallel_task_finished_event(result: ParallelTaskResult, *, status: str, error: Exception | None) -> dict:
    lines = _task_finished_lines(result, status=status, error=error)
    return build_parallel_task_finished(
        task_name=_sanitize(result.name),
        status=status,
        title="Parallel task finished",
        lines=lines,
    )


def build_parallel_merged_event(merge: ParallelMergeResult) -> dict:
    lines = [_sanitize(line) for line in merge.lines]
    return build_parallel_merged(
        title="Parallel merged",
        lines=lines,
    )


def _task_finished_lines(result: ParallelTaskResult, *, status: str, error: Exception | None) -> list[str]:
    lines: list[str] = []
    if status == "ok":
        lines.append(f"Task {result.name} finished.")
        if result.locals_update:
            names = ", ".join(sorted(result.locals_update.keys()))
            lines.append(f"Local updates are {names}.")
        else:
            lines.append("No local updates.")
    else:
        lines.append(f"Task {result.name} failed.")
        if error is not None:
            lines.append(f"Error was {error}.")
    return [_sanitize(line) for line in lines]


def _sanitize(value: object) -> str:
    text = "" if value is None else str(value)
    sanitized = text.translate(_BRACKET_CHARS)
    return " ".join(sanitized.split()).strip()


__all__ = [
    "build_parallel_merged_event",
    "build_parallel_started_event",
    "build_parallel_task_finished_event",
]
