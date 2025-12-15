from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.records.service import save_record_or_raise
from namel3ss.schema.records import RecordSchema


def handle_save(ctx: ExecutionContext, stmt: ir.Save) -> None:
    state_key = stmt.record_name.lower()
    data_obj = ctx.state.get(state_key)
    if not isinstance(data_obj, dict):
        raise Namel3ssError(
            f"Expected state.{state_key} to be a record dictionary",
            line=stmt.line,
            column=stmt.column,
        )
    validated = dict(data_obj)
    saved = save_record_or_raise(
        stmt.record_name,
        validated,
        ctx.schemas,
        ctx.state,
        ctx.store,
        line=stmt.line,
        column=stmt.column,
    )
    ctx.last_value = saved


def handle_find(ctx: ExecutionContext, stmt: ir.Find) -> None:
    schema = get_schema(ctx, stmt.record_name, stmt)

    def predicate(record: dict) -> bool:
        backup_locals = ctx.locals.copy()
        try:
            ctx.locals.update(record)
            result = evaluate_expression(ctx, stmt.predicate)
            if not isinstance(result, bool):
                raise Namel3ssError(
                    "Find predicate must evaluate to boolean",
                    line=stmt.line,
                    column=stmt.column,
                )
            return result
        finally:
            ctx.locals = backup_locals

    results = ctx.store.find(schema, predicate)
    result_name = f"{stmt.record_name.lower()}_results"
    ctx.locals[result_name] = results
    ctx.last_value = results


def get_schema(ctx: ExecutionContext, record_name: str, stmt: ir.Statement) -> RecordSchema:
    if record_name not in ctx.schemas:
        raise Namel3ssError(
            f"Unknown record '{record_name}'",
            line=stmt.line,
            column=stmt.column,
        )
    return ctx.schemas[record_name]
