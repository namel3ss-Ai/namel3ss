from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class ParallelTaskResult:
    name: str
    locals_update: dict[str, object]
    constants_update: set[str]
    traces: list[dict]
    last_value: object
    line: int | None
    column: int | None


@dataclass(frozen=True)
class ParallelMergeResult:
    locals: dict[str, object]
    constants: set[str]
    values: list[object]
    lines: list[str]


def merge_task_results(
    *,
    base_locals: dict[str, object],
    base_constants: set[str],
    results: list[ParallelTaskResult],
) -> ParallelMergeResult:
    merged_locals = dict(base_locals)
    merged_constants = set(base_constants)
    values: list[object] = []
    lines: list[str] = []
    updated: dict[str, str] = {}

    for result in results:
        values.append(result.last_value)
        if result.locals_update:
            names = sorted(result.locals_update.keys())
            for name in names:
                if name in updated:
                    raise Namel3ssError(
                        f"Parallel tasks cannot write the same local: {name}",
                        line=result.line,
                        column=result.column,
                    )
                updated[name] = result.name
                merged_locals[name] = result.locals_update[name]
            line = f"Task {result.name} updated locals {', '.join(names)}."
        else:
            line = f"Task {result.name} updated no locals."
        lines.append(line)

        if result.constants_update:
            merged_constants.update(result.constants_update)

    if not results:
        lines.append("No parallel tasks merged.")
    return ParallelMergeResult(
        locals=merged_locals,
        constants=merged_constants,
        values=values,
        lines=lines,
    )


__all__ = ["ParallelMergeResult", "ParallelTaskResult", "merge_task_results"]
