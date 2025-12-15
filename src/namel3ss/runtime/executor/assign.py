from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext


def assign(ctx: ExecutionContext, target: ir.Assignable, value: object, origin: ir.Statement) -> None:
    if isinstance(target, ir.VarReference):
        if target.name not in ctx.locals:
            raise Namel3ssError(
                f"Cannot set undeclared variable '{target.name}'",
                line=origin.line,
                column=origin.column,
            )
        if target.name in ctx.constants:
            raise Namel3ssError(
                f"Cannot set constant '{target.name}'",
                line=origin.line,
                column=origin.column,
            )
        ctx.locals[target.name] = value
        return

    if isinstance(target, ir.StatePath):
        assign_state_path(ctx.state, target, value)
        return

    raise Namel3ssError(f"Unsupported assignment target: {type(target)}", line=origin.line, column=origin.column)


def assign_state_path(state: Dict[str, object], target: ir.StatePath, value: object) -> None:
    cursor: Dict[str, object] = state
    for segment in target.path[:-1]:
        if segment not in cursor or not isinstance(cursor[segment], dict):
            cursor[segment] = {}
        cursor = cursor[segment]  # type: ignore[assignment]
    cursor[target.path[-1]] = value
