from __future__ import annotations

import re
from typing import Callable, Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema


def validate_record_instance(
    schema: RecordSchema,
    data: Dict[str, object],
    evaluate_expr: Callable[[object], object],
) -> None:
    for field in schema.fields:
        error = _field_error(schema.name, field, data, evaluate_expr)
        if error:
            raise Namel3ssError(error["message"])


def _field_error(
    record_name: str,
    field: FieldSchema,
    data: Dict[str, object],
    evaluate_expr: Callable[[object], object],
) -> Dict[str, str] | None:
    value = data.get(field.name)
    if field.constraint is None:
        return None
    constraint = field.constraint
    if constraint.kind == "present":
        if value is None:
            return {"field": field.name, "code": "present", "message": f"Field '{field.name}' in record '{record_name}' must be present"}
        return None
    if constraint.kind == "unique":
        return None
    if constraint.kind in {"gt", "lt"}:
        if not isinstance(value, (int, float)):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Field '{field.name}' in record '{record_name}' must be numeric",
            }
        compare_value = evaluate_expr(constraint.expression)
        if not isinstance(compare_value, (int, float)):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Constraint for field '{field.name}' in record '{record_name}' must be numeric",
            }
        if constraint.kind == "gt" and not (value > compare_value):
            return {
                "field": field.name,
                "code": "gt",
                "message": f"Field '{field.name}' in record '{record_name}' must be greater than {compare_value}",
            }
        if constraint.kind == "lt" and not (value < compare_value):
            return {
                "field": field.name,
                "code": "lt",
                "message": f"Field '{field.name}' in record '{record_name}' must be less than {compare_value}",
            }
        return None
    if constraint.kind in {"len_min", "len_max"}:
        if value is None:
            return {
                "field": field.name,
                "code": "present",
                "message": f"Field '{field.name}' in record '{record_name}' must be present for length check",
            }
        try:
            length = len(value)  # type: ignore[arg-type]
        except Exception:
            return {
                "field": field.name,
                "code": "type",
                "message": f"Field '{field.name}' in record '{record_name}' must support length checks",
            }
        compare_value = evaluate_expr(constraint.expression)
        if not isinstance(compare_value, (int, float)):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Constraint for field '{field.name}' in record '{record_name}' must be numeric",
            }
        if constraint.kind == "len_min" and length < compare_value:
            return {
                "field": field.name,
                "code": "min_length",
                "message": f"Field '{field.name}' in record '{record_name}' must have length at least {compare_value}",
            }
        if constraint.kind == "len_max" and length > compare_value:
            return {
                "field": field.name,
                "code": "max_length",
                "message": f"Field '{field.name}' in record '{record_name}' must have length at most {compare_value}",
            }
        return None
    if constraint.kind == "pattern":
        if not isinstance(value, str):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Field '{field.name}' in record '{record_name}' must be a string to match pattern",
            }
        if not re.fullmatch(constraint.pattern or "", value):
            return {
                "field": field.name,
                "code": "pattern",
                "message": f"Field '{field.name}' in record '{record_name}' must match pattern {constraint.pattern}",
            }
        return None
    return None


def collect_validation_errors(
    schema: RecordSchema,
    data: Dict[str, object],
    evaluate_expr: Callable[[object], object],
) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    for field in schema.fields:
        err = _field_error(schema.name, field, data, evaluate_expr)
        if err:
            errors.append(err)
    return errors
