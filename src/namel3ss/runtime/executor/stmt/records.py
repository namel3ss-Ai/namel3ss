from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.records_ops import handle_create, handle_delete, handle_find, handle_save, handle_update


def execute_save(ctx, stmt: ir.Save) -> None:
    _run_record_write(ctx, stmt, handle_save, kind="statement_save", verb="saved")


def execute_create(ctx, stmt: ir.Create) -> None:
    _run_record_write(ctx, stmt, handle_create, kind="statement_create", verb="created")


def execute_find(ctx, stmt: ir.Find) -> None:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot read records", line=stmt.line, column=stmt.column)
    handle_find(ctx, stmt)
    record_step(
        ctx,
        kind="statement_find",
        what=f"found {stmt.record_name}",
        line=stmt.line,
        column=stmt.column,
    )


def execute_update(ctx, stmt: ir.Update) -> None:
    _run_record_write(ctx, stmt, handle_update, kind="statement_update", verb="updated")


def execute_delete(ctx, stmt: ir.Delete) -> None:
    _run_record_write(ctx, stmt, handle_delete, kind="statement_delete", verb="deleted")


def _run_record_write(ctx, stmt: ir.Statement, handler, *, kind: str, verb: str) -> None:
    if getattr(ctx, "parallel_mode", False):
        raise Namel3ssError("Parallel tasks cannot write records", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot write records", line=stmt.line, column=stmt.column)
    handler(ctx, stmt)
    record_step(
        ctx,
        kind=kind,
        what=f"{verb} {stmt.record_name}",
        line=stmt.line,
        column=stmt.column,
    )


__all__ = ["execute_create", "execute_delete", "execute_find", "execute_save", "execute_update"]
