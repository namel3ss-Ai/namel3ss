from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SchemaType = Literal["string", "boolean", "number", "object", "array", "any"]


@dataclass(frozen=True)
class ContractField:
    name: str
    type_name: SchemaType
    required: bool = True
    default: object | None = None
    item_type: SchemaType | None = None
    ref: str | None = None
    item_ref: str | None = None
    stability: str = "additive"
    notes: str = ""


@dataclass(frozen=True)
class ContractSchema:
    name: str
    fields: tuple[ContractField, ...]
    additional_fields: bool = True
    notes: str = ""


def schema_to_payload(schema: ContractSchema) -> dict[str, object]:
    return {
        "name": schema.name,
        "notes": schema.notes,
        "additional_fields": schema.additional_fields,
        "fields": [field_to_payload(field) for field in schema.fields],
    }


def field_to_payload(field: ContractField) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": field.name,
        "type": field.type_name,
        "required": field.required,
        "default": _normalize_default(field.default),
        "stability": field.stability,
        "notes": field.notes,
    }
    if field.item_type is not None:
        payload["item_type"] = field.item_type
    if field.ref is not None:
        payload["ref"] = field.ref
    if field.item_ref is not None:
        payload["item_ref"] = field.item_ref
    return payload


def _normalize_default(value: object) -> object:
    if isinstance(value, tuple):
        return [_normalize_default(item) for item in value]
    if isinstance(value, list):
        return [_normalize_default(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_default(item) for key, item in value.items()}
    return value


__all__ = [
    "ContractField",
    "ContractSchema",
    "SchemaType",
    "field_to_payload",
    "schema_to_payload",
]
