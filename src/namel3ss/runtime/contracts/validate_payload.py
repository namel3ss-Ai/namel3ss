from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.runtime.contracts.runtime_schema import RUNTIME_CONTRACT_SCHEMAS
from namel3ss.runtime.contracts.schema_model import ContractField, ContractSchema


def validate_contract_payload(payload: object, *, schema_name: str) -> list[dict[str, str]]:
    schema = RUNTIME_CONTRACT_SCHEMAS.get(schema_name)
    if schema is None:
        return [_warning("schema.unknown", "$", f"Unknown contract schema '{schema_name}'.")]
    warnings: list[dict[str, str]] = []
    _validate_value(payload, schema=schema, path="$", warnings=warnings)
    return warnings


def validate_contract_payload_for_mode(
    payload: object,
    *,
    schema_name: str,
    ui_mode: str | None,
    diagnostics_enabled: bool = False,
) -> list[dict[str, str]]:
    if not contract_validation_enabled(ui_mode=ui_mode, diagnostics_enabled=diagnostics_enabled):
        return []
    return validate_contract_payload(payload, schema_name=schema_name)


def contract_validation_enabled(*, ui_mode: str | None, diagnostics_enabled: bool) -> bool:
    normalized_mode = str(ui_mode or "").strip().lower()
    return diagnostics_enabled or normalized_mode == "studio"


def with_contract_warnings(payload: object, warnings: Sequence[Mapping[str, object]]) -> object:
    if not isinstance(payload, dict):
        return payload
    normalized = _normalize_warnings(warnings)
    if not normalized:
        return payload
    copied = dict(payload)
    copied["contract_warnings"] = normalized
    return copied


def _validate_value(value: object, *, schema: ContractSchema, path: str, warnings: list[dict[str, str]]) -> None:
    if not isinstance(value, Mapping):
        warnings.append(
            _warning(
                "schema.type_mismatch",
                path,
                f"Expected object for '{schema.name}'.",
                expected="object",
                actual=_type_name(value),
            )
        )
        return
    for field in schema.fields:
        field_path = f"{path}.{field.name}"
        if field.name not in value:
            if field.required:
                warnings.append(
                    _warning(
                        "schema.missing_field",
                        field_path,
                        f"Missing required field '{field.name}'.",
                        expected=field.type_name,
                        actual="missing",
                    )
                )
            continue
        field_value = value[field.name]
        _validate_field(field_value, field=field, path=field_path, warnings=warnings)
    if schema.additional_fields:
        return
    allowed = {field.name for field in schema.fields}
    unknown = [key for key in value.keys() if isinstance(key, str) and key not in allowed]
    for key in sorted(unknown):
        warnings.append(_warning("schema.unknown_field", f"{path}.{key}", f"Unknown field '{key}' for '{schema.name}'."))


def _validate_field(value: object, *, field: ContractField, path: str, warnings: list[dict[str, str]]) -> None:
    if not _matches_type(value, field.type_name):
        warnings.append(
            _warning(
                "schema.type_mismatch",
                path,
                f"Expected '{field.type_name}' for field '{field.name}'.",
                expected=field.type_name,
                actual=_type_name(value),
            )
        )
        return
    if field.ref and isinstance(value, Mapping):
        ref_schema = RUNTIME_CONTRACT_SCHEMAS.get(field.ref)
        if ref_schema is None:
            warnings.append(_warning("schema.bad_ref", path, f"Unknown schema ref '{field.ref}'."))
            return
        _validate_value(value, schema=ref_schema, path=path, warnings=warnings)
        return
    if field.type_name != "array" or not isinstance(value, list):
        return
    for idx, item in enumerate(value):
        item_path = f"{path}[{idx}]"
        if field.item_ref:
            ref_schema = RUNTIME_CONTRACT_SCHEMAS.get(field.item_ref)
            if ref_schema is None:
                warnings.append(_warning("schema.bad_ref", item_path, f"Unknown schema ref '{field.item_ref}'."))
                continue
            _validate_value(item, schema=ref_schema, path=item_path, warnings=warnings)
            continue
        if field.item_type and not _matches_type(item, field.item_type):
            warnings.append(
                _warning(
                    "schema.type_mismatch",
                    item_path,
                    f"Expected '{field.item_type}' array item for field '{field.name}'.",
                    expected=field.item_type,
                    actual=_type_name(item),
                )
            )


def _matches_type(value: object, type_name: str) -> bool:
    if type_name == "any":
        return True
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, Mapping)
    if type_name == "array":
        return isinstance(value, list)
    return False


def _warning(
    code: str,
    path: str,
    message: str,
    *,
    expected: str | None = None,
    actual: str | None = None,
) -> dict[str, str]:
    warning = {
        "code": code,
        "path": path,
        "message": message,
    }
    if expected:
        warning["expected"] = expected
    if actual:
        warning["actual"] = actual
    return warning


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def _normalize_warnings(warnings: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for warning in warnings:
        if not isinstance(warning, Mapping):
            continue
        code = _text(warning.get("code"))
        path = _text(warning.get("path"))
        message = _text(warning.get("message"))
        if not code or not path or not message:
            continue
        entry = {
            "code": code,
            "path": path,
            "message": message,
        }
        expected = _text(warning.get("expected"))
        actual = _text(warning.get("actual"))
        if expected:
            entry["expected"] = expected
        if actual:
            entry["actual"] = actual
        normalized.append(entry)
    return normalized


def _text(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text
    return ""


__all__ = [
    "contract_validation_enabled",
    "validate_contract_payload",
    "validate_contract_payload_for_mode",
    "with_contract_warnings",
]
