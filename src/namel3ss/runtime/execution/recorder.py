from __future__ import annotations

from namel3ss.runtime.execution.step import ExecutionStep


def record_step(
    ctx,
    kind: str,
    what: str,
    *,
    because: str | None = None,
    data: dict | None = None,
    line: int | None = None,
    column: int | None = None,
) -> ExecutionStep:
    counter = getattr(ctx, "execution_step_counter", 0) + 1
    setattr(ctx, "execution_step_counter", counter)
    step_id = _step_id(counter)
    step = ExecutionStep(
        id=step_id,
        kind=kind,
        what=what,
        because=because,
        data=data or {},
        line=line,
        column=column,
    )
    steps = getattr(ctx, "execution_steps", None)
    if isinstance(steps, list):
        steps.append(step.as_dict())
    return step


def _step_id(counter: int) -> str:
    return f"step:{counter:04d}"


__all__ = ["record_step"]
