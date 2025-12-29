from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir


@dataclass(frozen=True)
class ParallelPlan:
    tasks: list[ir.ParallelTask]


def build_parallel_plan(block: ir.ParallelBlock) -> ParallelPlan:
    tasks = list(block.tasks or [])
    if not tasks:
        raise Namel3ssError("Parallel block requires at least one task", line=block.line, column=block.column)
    ordered = sorted(tasks, key=lambda task: task.name)
    seen: set[str] = set()
    for task in ordered:
        name = str(task.name or "").strip()
        if not name:
            raise Namel3ssError("Parallel task name cannot be empty", line=task.line, column=task.column)
        if name in seen:
            raise Namel3ssError("Parallel task names must be unique", line=task.line, column=task.column)
        seen.add(name)
    return ParallelPlan(tasks=ordered)


__all__ = ["ParallelPlan", "build_parallel_plan"]
