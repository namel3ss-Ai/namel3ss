from __future__ import annotations

from typing import Dict, List

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.validators.constraints import collect_validation_errors
from namel3ss.schema.identity import IdentitySchema
from namel3ss.schema.records import FieldSchema, RecordSchema
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.validation import ValidationMode, add_warning


def resolve_identity(
    config: AppConfig | None,
    schema: IdentitySchema | None,
    *,
    mode: ValidationMode = ValidationMode.RUNTIME,
    warnings: list | None = None,
) -> dict:
    identity = dict(config.identity.defaults) if config else {}
    if schema is None:
        return identity
    if mode == ValidationMode.STATIC:
        try:
            _validate_identity(schema, identity)
        except Namel3ssError as err:
            add_warning(
                warnings,
                code="identity.missing",
                message=str(err),
                fix="Provide N3_IDENTITY_* values or declare defaults; runtime will enforce.",
                path="identity",
                line=schema.line,
                column=schema.column,
                enforced_at="runtime",
            )
            return identity
        return identity
    _validate_identity(schema, identity)
    return identity


def _validate_identity(schema: IdentitySchema, identity: dict) -> None:
    errors = _type_errors(schema.fields, identity, schema.name)
    if errors:
        raise Namel3ssError(
            _identity_type_message(errors[0]["field"], errors[0]["expected"]),
            line=schema.line,
            column=schema.column,
        )
    record_schema = RecordSchema(name=f"identity.{schema.name}", fields=schema.fields)
    constraint_errors = collect_validation_errors(record_schema, identity, _literal_eval)
    if constraint_errors:
        err = constraint_errors[0]
        raise Namel3ssError(
            _identity_constraint_message(err["field"], err["message"]),
            line=schema.line,
            column=schema.column,
        )
    if schema.trust_levels is not None:
        trust_value = identity.get("trust_level")
        if trust_value is None:
            raise Namel3ssError(
                _trust_level_missing_message(schema.trust_levels),
                line=schema.line,
                column=schema.column,
            )
        if trust_value not in schema.trust_levels:
            raise Namel3ssError(
                _trust_level_invalid_message(trust_value, schema.trust_levels),
                line=schema.line,
                column=schema.column,
            )


def _type_errors(fields: List[FieldSchema], identity: dict, name: str) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    for field in fields:
        value = identity.get(field.name)
        if value is None:
            continue
        expected = field.type_name
        if expected == "text" and not isinstance(value, str):
            errors.append({"field": field.name, "expected": "text"})
        elif expected == "number" and not is_number(value):
            errors.append({"field": field.name, "expected": "number"})
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append({"field": field.name, "expected": "boolean"})
        elif expected == "json" and not isinstance(value, (dict, list)):
            errors.append({"field": field.name, "expected": "json"})
    return errors


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
    raise Namel3ssError(
        build_guidance_message(
            what="Identity constraint requires a literal value.",
            why="Only literal expressions are supported in identity constraints for now.",
            fix="Replace the expression with a literal value.",
            example='field "trust" is number must be greater than 1',
        )
    )


def _identity_type_message(field: str, expected: str) -> str:
    return build_guidance_message(
        what=f"Identity field '{field}' must be {expected}.",
        why="The identity declaration defines a different type for this field.",
        fix="Provide a value that matches the declared type.",
        example="N3_IDENTITY_EMAIL=dev@example.com",
    )


def _identity_constraint_message(field: str, details: str) -> str:
    return build_guidance_message(
        what=f"Identity field '{field}' failed validation.",
        why=details,
        fix="Provide an identity value that satisfies the declared constraint.",
        example="N3_IDENTITY_EMAIL=dev@example.com",
    )


def _trust_level_missing_message(allowed: List[str]) -> str:
    return build_guidance_message(
        what="Identity is missing trust_level.",
        why=f"Allowed trust levels: {', '.join(allowed)}.",
        fix="Provide a trust_level value in your identity defaults.",
        example=f"N3_IDENTITY_TRUST_LEVEL={allowed[0] if allowed else 'guest'}",
    )


def _trust_level_invalid_message(value: object, allowed: List[str]) -> str:
    return build_guidance_message(
        what=f"Identity trust_level '{value}' is not allowed.",
        why=f"Allowed trust levels: {', '.join(allowed)}.",
        fix="Provide a trust_level value that matches the declaration.",
        example=f"N3_IDENTITY_TRUST_LEVEL={allowed[0] if allowed else 'guest'}",
    )
