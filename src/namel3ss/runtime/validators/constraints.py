from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema
from namel3ss.utils.numbers import is_number, to_decimal


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
    if constraint.kind in {"gt", "gte", "lt", "lte", "between"}:
        if not is_number(value):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Field '{field.name}' in record '{record_name}' must be numeric",
            }
        left = to_decimal(value)
        if constraint.kind == "between":
            low = evaluate_expr(constraint.expression)
            high = evaluate_expr(constraint.expression_high)
            if not is_number(low) or not is_number(high):
                return {
                    "field": field.name,
                    "code": "type",
                    "message": f"Constraint for field '{field.name}' in record '{record_name}' must be numeric",
                }
            low_value = to_decimal(low)
            high_value = to_decimal(high)
            if low_value > high_value:
                return {
                    "field": field.name,
                    "code": "between",
                    "message": f"Field '{field.name}' in record '{record_name}' has an invalid between range",
                }
            if left < low_value or left > high_value:
                return {
                    "field": field.name,
                    "code": "between",
                    "message": f"Field '{field.name}' in record '{record_name}' must be between {low} and {high}",
                }
            return None
        compare_value = evaluate_expr(constraint.expression)
        if not is_number(compare_value):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Constraint for field '{field.name}' in record '{record_name}' must be numeric",
            }
        right = to_decimal(compare_value)
        if constraint.kind == "gt" and not (left > right):
            return {
                "field": field.name,
                "code": "gt",
                "message": f"Field '{field.name}' in record '{record_name}' must be greater than {compare_value}",
            }
        if constraint.kind == "gte" and not (left >= right):
            return {
                "field": field.name,
                "code": "gte",
                "message": f"Field '{field.name}' in record '{record_name}' must be at least {compare_value}",
            }
        if constraint.kind == "lt" and not (left < right):
            return {
                "field": field.name,
                "code": "lt",
                "message": f"Field '{field.name}' in record '{record_name}' must be less than {compare_value}",
            }
        if constraint.kind == "lte" and not (left <= right):
            return {
                "field": field.name,
                "code": "lte",
                "message": f"Field '{field.name}' in record '{record_name}' must be at most {compare_value}",
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
        if not is_number(compare_value):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Constraint for field '{field.name}' in record '{record_name}' must be numeric",
            }
        compare_decimal = to_decimal(compare_value)
        if constraint.kind == "len_min" and to_decimal(length) < compare_decimal:
            return {
                "field": field.name,
                "code": "min_length",
                "message": f"Field '{field.name}' in record '{record_name}' must have length at least {compare_value}",
            }
        if constraint.kind == "len_max" and to_decimal(length) > compare_decimal:
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
    if constraint.kind == "int":
        if not is_number(value):
            return {
                "field": field.name,
                "code": "type",
                "message": f"Field '{field.name}' in record '{record_name}' must be numeric",
            }
        numeric = to_decimal(value)
        if not numeric == numeric.to_integral_value():
            return {
                "field": field.name,
                "code": "int",
                "message": f"Field '{field.name}' in record '{record_name}' must be an integer",
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
