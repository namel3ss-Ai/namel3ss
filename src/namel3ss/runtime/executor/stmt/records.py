from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.records_ops import handle_create, handle_delete, handle_find, handle_save, handle_update
from namel3ss.runtime.flow.ids import flow_step_id
from namel3ss.runtime.mutation_policy import evaluate_mutation_policy
from namel3ss.traces.schema import TraceEventType


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


def execute_update(ctx, stmt: ir.Update, *, deterministic: bool = False) -> None:
    _run_record_write(ctx, stmt, handle_update, kind="statement_update", verb="updated", deterministic=deterministic)


def execute_delete(ctx, stmt: ir.Delete, *, deterministic: bool = False) -> None:
    _run_record_write(ctx, stmt, handle_delete, kind="statement_delete", verb="deleted", deterministic=deterministic)


def _run_record_write(ctx, stmt: ir.Statement, handler, *, kind: str, verb: str, deterministic: bool = False) -> None:
    if getattr(ctx, "parallel_mode", False):
        raise Namel3ssError("Parallel tasks cannot write records", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot write records", line=stmt.line, column=stmt.column)
    action = _mutation_action(stmt)
    decision = evaluate_mutation_policy(
        ctx,
        action=action,
        record=stmt.record_name,
        line=getattr(stmt, "line", None),
        column=getattr(stmt, "column", None),
    )
    step_id = _mutation_step_id(ctx, action)
    if not decision.allowed:
        _record_mutation_blocked(ctx, stmt, action, decision, step_id)
        raise Namel3ssError(
            decision.error_message or decision.message or "Mutation blocked by policy.",
            line=stmt.line,
            column=stmt.column,
            details={
                "category": "policy",
                "reason_code": decision.reason_code,
                "flow_name": getattr(getattr(ctx, "flow", None), "name", None),
                "record": stmt.record_name,
                "action": action,
                "step_id": step_id,
            },
        )
    _record_mutation_allowed(ctx, stmt, action, step_id)
    handler(ctx, stmt, deterministic=deterministic)
    record_step(
        ctx,
        kind=kind,
        what=f"{verb} {stmt.record_name}",
        line=stmt.line,
        column=stmt.column,
    )


def _mutation_action(stmt: ir.Statement) -> str:
    if isinstance(stmt, ir.Save):
        return "save"
    if isinstance(stmt, ir.Create):
        return "create"
    if isinstance(stmt, ir.Update):
        return "update"
    if isinstance(stmt, ir.Delete):
        return "delete"
    return "mutation"


def _mutation_step_id(ctx, action: str) -> str | None:
    flow = getattr(ctx, "flow", None)
    if not flow:
        return None
    ordinal = getattr(ctx, "current_statement_index", None)
    if not isinstance(ordinal, int) or ordinal < 1:
        ordinal = 0
    return flow_step_id(flow.name, action, ordinal)


def _record_mutation_allowed(ctx, stmt: ir.Statement, action: str, step_id: str | None) -> None:
    entry = {
        "type": TraceEventType.MUTATION_ALLOWED,
        "flow_name": getattr(getattr(ctx, "flow", None), "name", None),
        "step_id": step_id,
        "record": stmt.record_name,
        "action": action,
    }
    ctx.traces.append(entry)


def _record_mutation_blocked(ctx, stmt: ir.Statement, action: str, decision, step_id: str | None) -> None:
    entry = {
        "type": TraceEventType.MUTATION_BLOCKED,
        "flow_name": getattr(getattr(ctx, "flow", None), "name", None),
        "step_id": step_id,
        "record": stmt.record_name,
        "action": action,
        "reason_code": decision.reason_code,
        "message": decision.message,
        "fix_hint": decision.fix_hint,
    }
    ctx.traces.append(entry)


__all__ = ["execute_create", "execute_delete", "execute_find", "execute_save", "execute_update"]
