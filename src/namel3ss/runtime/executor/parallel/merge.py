from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class ParallelTaskResult:
    name: str
    locals_update: dict[str, object]
    constants_update: set[str]
    traces: list[dict]
    yield_messages: list[dict]
    last_value: object
    line: int | None
    column: int | None


@dataclass(frozen=True)
class ParallelMergeResult:
    locals: dict[str, object]
    constants: set[str]
    values: list[object]
    yield_messages: list[dict]
    lines: list[str]
    policy: str
    conflicts: list[str]


def merge_task_results(
    *,
    base_locals: dict[str, object],
    base_constants: set[str],
    results: list[ParallelTaskResult],
    policy: str | None = None,
) -> ParallelMergeResult:
    resolved_policy = policy or "conflict"
    if resolved_policy not in {"conflict", "precedence", "override"}:
        raise Namel3ssError(f"Unknown parallel merge policy '{resolved_policy}'.")
    merged_locals = dict(base_locals)
    merged_constants = set(base_constants)
    values: list[object] = []
    merged_yields: list[dict] = []
    lines: list[str] = []
    conflict_lines: list[str] = []
    conflicts: list[str] = []
    updated: dict[str, str] = {}

    for result in results:
        values.append(result.last_value)
        if result.yield_messages:
            merged_yields.extend(result.yield_messages)
        if result.locals_update:
            names = sorted(result.locals_update.keys())
            for name in names:
                if name in updated:
                    if resolved_policy == "conflict":
                        raise Namel3ssError(
                            f"Parallel tasks cannot write the same local: {name}",
                            line=result.line,
                            column=result.column,
                        )
                    conflicts.append(name)
                    if resolved_policy == "precedence":
                        conflict_lines.append(f"Conflict on {name} kept from {updated[name]}.")
                        continue
                    conflict_lines.append(f"Conflict on {name} overridden by {result.name}.")
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
    if conflict_lines:
        lines.extend(conflict_lines)
    return ParallelMergeResult(
        locals=merged_locals,
        constants=merged_constants,
        values=values,
        yield_messages=merged_yields,
        lines=lines,
        policy=resolved_policy,
        conflicts=sorted(set(conflicts)),
    )


__all__ = ["ParallelMergeResult", "ParallelTaskResult", "merge_task_results"]
