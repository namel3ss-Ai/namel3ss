from __future__ import annotations

from decimal import Decimal
import time
from typing import Dict, List, Optional, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.validators.constraints import collect_validation_errors
from namel3ss.schema.records import (
    EXPIRES_AT_FIELD,
    SYSTEM_FIELDS,
    TENANT_KEY_FIELD,
    RecordSchema,
)
from namel3ss.runtime.storage.base import RecordScope
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def save_record_or_raise(
    record_name: str,
    values: Dict[str, object],
    schemas: Dict[str, RecordSchema],
    state: Dict[str, object],
    store: Storage,
    identity: dict | None = None,
    line: int | None = None,
    column: int | None = None,
) -> dict:
    saved, errors = save_record_with_errors(record_name, values, schemas, state, store, identity=identity)
    if errors:
        first = errors[0]
        raise Namel3ssError(first["message"], line=line, column=column)
    return saved


def validate_record_values(
    record_name: str,
    values: Dict[str, object],
    schemas: Dict[str, RecordSchema],
    line: int | None = None,
    column: int | None = None,
) -> Dict[str, object]:
    schema = _get_schema(record_name, schemas)
    type_errors = _type_errors(schema, values)
    if type_errors:
        raise Namel3ssError(type_errors[0]["message"], line=line, column=column)
    constraint_errors = collect_validation_errors(schema, values, _literal_eval)
    if constraint_errors:
        raise Namel3ssError(constraint_errors[0]["message"], line=line, column=column)
    return values


def save_record_with_errors(
    record_name: str,
    values: Dict[str, object],
    schemas: Dict[str, RecordSchema],
    state: Dict[str, object],
    store: Storage,
    identity: dict | None = None,
) -> Tuple[Optional[dict], List[Dict[str, str]]]:
    schema = _get_schema(record_name, schemas)
    prepared = dict(values)
    try:
        scope = build_record_scope(schema, identity)
        _apply_system_fields(schema, prepared, scope)
    except Namel3ssError as exc:
        return None, [
            {
                "field": "tenant_key",
                "code": "tenant",
                "message": str(exc),
            }
        ]
    type_errors = _type_errors(schema, values)
    if type_errors:
        return None, type_errors

    constraint_errors = collect_validation_errors(schema, values, _literal_eval)
    if constraint_errors:
        return None, constraint_errors

    conflict_field = store.check_unique(schema, prepared, scope=scope)
    if conflict_field:
        return None, [
            {
                "field": conflict_field,
                "code": "unique",
                "message": f"Field '{conflict_field}' in record '{record_name}' must be unique",
            }
        ]
    try:
        saved = store.save(schema, prepared)
        return strip_system_fields(saved), []
    except Namel3ssError as exc:
        # Fallback for any residual unique enforcement
        return None, [
            {
                "field": conflict_field or "",
                "code": "unique",
                "message": str(exc),
            }
        ]


def _type_errors(schema: RecordSchema, data: Dict[str, object]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    for field in schema.fields:
        value = data.get(field.name)
        if value is None:
            continue
        expected = field.type_name
        if expected == "string" and not isinstance(value, str):
            errors.append(_type_error(field.name, schema.name, "string"))
        elif expected == "int":
            if isinstance(value, bool):
                errors.append(_type_error(field.name, schema.name, "int"))
            elif isinstance(value, int):
                pass
            elif is_number(value):
                if not decimal_is_int(to_decimal(value)):
                    errors.append(_type_error(field.name, schema.name, "int"))
            else:
                errors.append(_type_error(field.name, schema.name, "int"))
        elif expected == "number" and not is_number(value):
            errors.append(_type_error(field.name, schema.name, "number"))
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append(_type_error(field.name, schema.name, "boolean"))
    return errors


def _type_error(field: str, record: str, expected: str) -> Dict[str, str]:
    return {
        "field": field,
        "code": "type",
        "message": f"Field '{field}' in record '{record}' must be a {expected}",
    }


def _get_schema(name: str, schemas: Dict[str, RecordSchema]) -> RecordSchema:
    if name not in schemas:
        raise Namel3ssError(f"Unknown record '{name}'")
    return schemas[name]


def _literal_eval(expr: ir.Expression | None) -> object:
    if expr is None:
        return None
    if isinstance(expr, ir.Literal):
        return expr.value
    if isinstance(expr, ir.UnaryOp) and expr.op in {"+", "-"}:
        if isinstance(expr.operand, ir.Literal):
            value = expr.operand.value
            if is_number(value):
                numeric = to_decimal(value)
                return numeric if expr.op == "+" else -numeric
    raise Namel3ssError("Only literal expressions supported in schema constraints for forms")


def build_record_scope(schema: RecordSchema, identity: dict | None, now: Decimal | None = None) -> RecordScope:
    tenant_value = None
    if schema.tenant_key:
        tenant_value = _resolve_tenant_value(schema, identity)
    if schema.ttl_hours is not None:
        now = now or _now_decimal()
    return RecordScope(tenant_value=tenant_value, now=now)


def strip_system_fields(record: dict | None) -> dict | None:
    if record is None:
        return None
    return {key: value for key, value in record.items() if key not in SYSTEM_FIELDS}


def _apply_system_fields(schema: RecordSchema, values: dict, scope: RecordScope) -> None:
    if schema.tenant_key:
        values[TENANT_KEY_FIELD] = scope.tenant_value
    if schema.ttl_hours is not None:
        expires_at = _compute_expires_at(schema.ttl_hours, scope.now)
        values[EXPIRES_AT_FIELD] = expires_at


def _compute_expires_at(ttl_hours: Decimal, now: Decimal | None) -> Decimal:
    current = now or _now_decimal()
    return current + (ttl_hours * Decimal("3600"))


def _resolve_tenant_value(schema: RecordSchema, identity: dict | None) -> str:
    if identity is None:
        raise Namel3ssError(_tenant_missing_message(schema))
    current: object = identity
    path = schema.tenant_key or []
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise Namel3ssError(_tenant_missing_message(schema))
        current = current.get(part)
    if current is None:
        raise Namel3ssError(_tenant_missing_message(schema))
    if not isinstance(current, str):
        raise Namel3ssError(_tenant_type_message(schema, current))
    return current


def _tenant_missing_message(schema: RecordSchema) -> str:
    path = ".".join(schema.tenant_key or [])
    field = path or "<field>"
    return build_guidance_message(
        what=f"Record '{schema.name}' requires a tenant identity.",
        why=f"tenant_key is set to identity.{field}, but no tenant value was provided.",
        fix="Provide the tenant field in identity defaults or engine identity.",
        example=f"N3_IDENTITY_{(schema.tenant_key or ['ORG_ID'])[-1].upper()}=acme",
    )


def _tenant_type_message(schema: RecordSchema, value: object) -> str:
    path = ".".join(schema.tenant_key or [])
    field = path or "<field>"
    return build_guidance_message(
        what=f"Record '{schema.name}' tenant_key must be text.",
        why=f"identity.{field} resolved to {type(value).__name__}, but tenant_key expects text.",
        fix="Provide a string identity value for the tenant key.",
        example=f"N3_IDENTITY_{(schema.tenant_key or ['ORG_ID'])[-1].upper()}=acme",
    )


def _now_decimal() -> Decimal:
    return Decimal(str(time.time()))
