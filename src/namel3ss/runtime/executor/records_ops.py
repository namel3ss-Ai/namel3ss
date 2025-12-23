from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.records.service import save_record_or_raise
from namel3ss.runtime.records.state_paths import get_state_record, record_state_path
from namel3ss.schema.records import RecordSchema


def handle_save(ctx: ExecutionContext, stmt: ir.Save) -> None:
    data_obj = get_state_record(ctx.state, stmt.record_name)
    if not isinstance(data_obj, dict):
        state_path = ".".join(record_state_path(stmt.record_name))
        raise Namel3ssError(
            f"Expected state.{state_path} to be a record dictionary",
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


def handle_create(ctx: ExecutionContext, stmt: ir.Create) -> None:
    values = evaluate_expression(ctx, stmt.values)
    if not isinstance(values, dict):
        raise Namel3ssError(
            _create_values_message(values),
            line=stmt.line,
            column=stmt.column,
        )
    saved = save_record_or_raise(
        stmt.record_name,
        dict(values),
        ctx.schemas,
        ctx.state,
        ctx.store,
        line=stmt.line,
        column=stmt.column,
    )
    ctx.locals[stmt.target] = saved
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
    path = record_state_path(stmt.record_name)
    result_name = f"{'_'.join(path)}_results"
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


def _create_values_message(values: object) -> str:
    return build_guidance_message(
        what="Create expects a record dictionary of values.",
        why=f"The provided value is {_value_kind(values)}, but create needs key/value fields to validate and save.",
        fix="Pass a dictionary (for example, state.order or an input payload).",
        example='create "Order" with state.order as order',
    )


def _value_kind(value: object) -> str:
    from namel3ss.utils.numbers import is_number

    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    return type(value).__name__
