from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.validators.constraints import collect_validation_errors, validate_record_instance
from namel3ss.schema.records import RecordSchema


def save_record_or_raise(
    record_name: str,
    values: Dict[str, object],
    schemas: Dict[str, RecordSchema],
    state: Dict[str, object],
    store: MemoryStore,
    line: int | None = None,
    column: int | None = None,
) -> dict:
    saved, errors = save_record_with_errors(record_name, values, schemas, state, store)
    if errors:
        first = errors[0]
        raise Namel3ssError(first["message"], line=line, column=column)
    return saved


def save_record_with_errors(
    record_name: str,
    values: Dict[str, object],
    schemas: Dict[str, RecordSchema],
    state: Dict[str, object],
    store: MemoryStore,
) -> Tuple[Optional[dict], List[Dict[str, str]]]:
    schema = _get_schema(record_name, schemas)
    type_errors = _type_errors(schema, values)
    if type_errors:
        return None, type_errors

    constraint_errors = collect_validation_errors(schema, values, _literal_eval)
    if constraint_errors:
        return None, constraint_errors

    conflict_field = store.check_unique(schema, values)
    if conflict_field:
        return None, [
            {
                "field": conflict_field,
                "code": "unique",
                "message": f"Field '{conflict_field}' in record '{record_name}' must be unique",
            }
        ]
    try:
        saved = store.save(schema, values)
        return saved, []
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
        elif expected == "int" and not isinstance(value, int):
            errors.append(_type_error(field.name, schema.name, "int"))
        elif expected == "number" and not isinstance(value, (int, float)):
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
    raise Namel3ssError("Only literal expressions supported in schema constraints for forms")

