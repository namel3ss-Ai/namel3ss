from __future__ import annotations

import os
from typing import Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.predicate_sql import compile_sql_predicate
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.records.service import build_record_scope, save_record_or_raise, validate_record_values
from namel3ss.runtime.records.state_paths import get_state_record, record_state_path
from namel3ss.runtime.storage.predicate import PredicatePlan
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.schema.records import RecordSchema
from namel3ss.secrets import collect_secret_values


def handle_save(ctx: ExecutionContext, stmt: ir.Save) -> None:
    data_obj = get_state_record(ctx.state, stmt.record_name)
    if not isinstance(data_obj, dict):
        state_path = ".".join(record_state_path(stmt.record_name))
        raise Namel3ssError(
            f"Expected state.{state_path} to be a record dictionary",
            line=stmt.line,
            column=stmt.column,
        )
    schema = get_schema(ctx, stmt.record_name, stmt)
    _coerce_text_fields(ctx, schema, data_obj, line=stmt.line, column=stmt.column)
    validated = dict(data_obj)
    saved = save_record_or_raise(
        stmt.record_name,
        validated,
        ctx.schemas,
        ctx.state,
        ctx.store,
        identity=ctx.identity,
        line=stmt.line,
        column=stmt.column,
    )
    _record_change(ctx, stmt.record_name, saved)
    ctx.last_value = saved


def handle_create(ctx: ExecutionContext, stmt: ir.Create) -> None:
    values = evaluate_expression(ctx, stmt.values)
    if not isinstance(values, dict):
        raise Namel3ssError(
            _create_values_message(values),
            line=stmt.line,
            column=stmt.column,
        )
    schema = get_schema(ctx, stmt.record_name, stmt)
    _coerce_text_fields(ctx, schema, values, line=stmt.line, column=stmt.column)
    saved = save_record_or_raise(
        stmt.record_name,
        dict(values),
        ctx.schemas,
        ctx.state,
        ctx.store,
        identity=ctx.identity,
        line=stmt.line,
        column=stmt.column,
    )
    _record_change(ctx, stmt.record_name, saved)
    ctx.locals[stmt.target] = saved
    ctx.last_value = saved


def handle_find(ctx: ExecutionContext, stmt: ir.Find) -> None:
    schema = get_schema(ctx, stmt.record_name, stmt)
    predicate = build_predicate_plan(ctx, schema, stmt.predicate, subject="Find", line=stmt.line, column=stmt.column)

    try:
        scope = build_record_scope(schema, ctx.identity)
    except Namel3ssError as exc:
        raise Namel3ssError(str(exc), line=stmt.line, column=stmt.column) from exc
    results = ctx.store.find(schema, predicate, scope=scope)
    path = record_state_path(stmt.record_name)
    result_name = f"{'_'.join(path)}_results"
    ctx.locals[result_name] = results
    ctx.last_value = results


def handle_update(ctx: ExecutionContext, stmt: ir.Update) -> None:
    if stmt.record_name not in ctx.schemas:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown record '{stmt.record_name}'.",
                why="Update requires a record declared in app.ai.",
                fix="Define the record or update the record name.",
                example=f'record "{stmt.record_name}":\\n  field \"id\" is number',
            ),
            line=stmt.line,
            column=stmt.column,
        )
    schema = ctx.schemas[stmt.record_name]
    for update in stmt.updates:
        if update.name not in schema.field_map:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown field '{update.name}' in record '{schema.name}'.",
                    why="Update assignments must match declared record fields.",
                    fix="Use a field declared on the record.",
                    example=f'update "{schema.name}" where id is 1 set:\\n  {next(iter(schema.field_map), "field")} is "value"',
                ),
                line=update.line,
                column=update.column,
            )
    predicate = build_predicate_plan(ctx, schema, stmt.predicate, subject="Update", line=stmt.line, column=stmt.column)
    scope = build_record_scope(schema, ctx.identity)
    results = ctx.store.find(schema, predicate, scope=scope)
    updated = 0
    for record in results:
        updated_record = _apply_updates(ctx, record, stmt.updates)
        _coerce_text_fields(ctx, schema, updated_record, line=stmt.line, column=stmt.column)
        validate_record_values(
            stmt.record_name,
            updated_record,
            ctx.schemas,
            line=stmt.line,
            column=stmt.column,
        )
        saved = ctx.store.update(schema, updated_record)
        _record_change(ctx, stmt.record_name, saved)
        updated += 1
    ctx.last_value = updated


def handle_delete(ctx: ExecutionContext, stmt: ir.Delete) -> None:
    if stmt.record_name not in ctx.schemas:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown record '{stmt.record_name}'.",
                why="Delete requires a record declared in app.ai.",
                fix="Define the record or update the record name.",
                example=f'record "{stmt.record_name}":\\n  field \"id\" is number',
            ),
            line=stmt.line,
            column=stmt.column,
        )
    schema = ctx.schemas[stmt.record_name]
    predicate = build_predicate_plan(ctx, schema, stmt.predicate, subject="Delete", line=stmt.line, column=stmt.column)
    scope = build_record_scope(schema, ctx.identity)
    results = ctx.store.find(schema, predicate, scope=scope)
    deleted = 0
    id_col = "id" if "id" in schema.field_map else "_id"
    for record in results:
        record_id = record.get(id_col)
        if record_id is None:
            raise Namel3ssError(
                f"Record '{schema.name}' delete requires {id_col}",
                line=stmt.line,
                column=stmt.column,
            )
        if ctx.store.delete(schema, record_id):
            _record_change(ctx, stmt.record_name, record)
            deleted += 1
    ctx.last_value = deleted


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


def _record_change(ctx: ExecutionContext, record_name: str, saved: dict) -> None:
    if not isinstance(saved, dict):
        return
    record_id = saved.get("id") if "id" in saved else saved.get("_id")
    if record_id is None:
        return
    ctx.record_changes.append({"record": record_name, "id": record_id})


def _coerce_text_fields(
    ctx: ExecutionContext,
    schema: RecordSchema,
    values: dict,
    *,
    line: int | None,
    column: int | None,
) -> None:
    secret_values: list[str] | None = None
    for field in schema.fields:
        if field.type_name not in {"text", "string"}:
            continue
        if field.name not in values:
            continue
        value = values.get(field.name)
        if value is None or isinstance(value, str):
            continue
        if _strict_text_fields_enabled():
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Expected text for {schema.name}.{field.name}.",
                    why=f"Got {type_name_for_value(value)} instead.",
                    fix="Convert the value to text before saving.",
                    example=f'set state.record.{field.name} is "example"',
                ),
                line=line,
                column=column,
            )
        if secret_values is None:
            secret_values = collect_secret_values(ctx.config)
        values[field.name] = normalize_ai_text(
            value,
            provider_name=ctx.last_ai_provider,
            secret_values=secret_values,
        )
        event = {
            "type": "type_mismatch_coerced",
            "record": schema.name,
            "field": field.name,
            "expected": "text",
            "actual": type_name_for_value(value),
        }
        if ctx.last_ai_provider:
            event["provider"] = ctx.last_ai_provider
        if line is not None:
            event["line"] = line
        if column is not None:
            event["column"] = column
        ctx.traces.append(event)


def _strict_text_fields_enabled() -> bool:
    value = os.getenv("NAMEL3SS_STRICT_TEXT_FIELDS")
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no"}


def build_predicate_plan(
    ctx: ExecutionContext,
    schema: RecordSchema,
    predicate: ir.Expression,
    *,
    subject: str,
    line: int | None,
    column: int | None,
) -> PredicatePlan:
    predicate_fn = _build_predicate_fn(ctx, predicate, subject=subject, line=line, column=column)
    sql_predicate = None
    reason = None
    dialect = getattr(ctx.store, "dialect", None)
    if dialect in {"sqlite", "postgres"}:
        sql_predicate, reason = compile_sql_predicate(ctx, schema, predicate, dialect=dialect)
    return PredicatePlan(predicate=predicate_fn, sql=sql_predicate, sql_reason=reason)


def _build_predicate_fn(
    ctx: ExecutionContext,
    predicate: ir.Expression,
    *,
    subject: str,
    line: int | None,
    column: int | None,
) -> Callable[[dict], bool]:
    def _predicate(record: dict) -> bool:
        backup_locals = ctx.locals.copy()
        try:
            ctx.locals.update(record)
            result = evaluate_expression(ctx, predicate)
            if not isinstance(result, bool):
                raise Namel3ssError(
                    f"{subject} predicate must evaluate to boolean",
                    line=line,
                    column=column,
                )
            return result
        finally:
            ctx.locals = backup_locals

    return _predicate


def _apply_updates(ctx: ExecutionContext, record: dict, updates: list[ir.UpdateField]) -> dict:
    backup_locals = ctx.locals.copy()
    try:
        ctx.locals.update(record)
        updated = dict(record)
        for update in updates:
            updated[update.name] = evaluate_expression(ctx, update.expression)
        return updated
    finally:
        ctx.locals = backup_locals
