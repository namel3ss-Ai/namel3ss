from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir

SUPPORTED_TYPES = {
    "text",
    "string",
    "str",
    "number",
    "int",
    "integer",
    "boolean",
    "bool",
    "json",
    "list",
    "map",
}

TENANT_KEY_FIELD = "__n3_tenant_key"
EXPIRES_AT_FIELD = "__n3_expires_at"
SYSTEM_FIELDS = {TENANT_KEY_FIELD, EXPIRES_AT_FIELD}


@dataclass
class FieldConstraint:
    kind: str  # present, unique, gt, gte, lt, lte, between, int, pattern, len_min, len_max
    expression: Optional[ir.Expression] = None
    expression_high: Optional[ir.Expression] = None
    pattern: Optional[str] = None


@dataclass
class FieldSchema:
    name: str
    type_name: str
    constraint: Optional[FieldConstraint] = None


@dataclass
class RecordSchema:
    name: str
    fields: List[FieldSchema] = field(default_factory=list)
    tenant_key: List[str] | None = None
    ttl_hours: Decimal | None = None
    system_fields: List[FieldSchema] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._validate_schema()
        self.field_map: Dict[str, FieldSchema] = {f.name: f for f in self.fields}
        self.unique_fields = {f.name for f in self.fields if f.constraint and f.constraint.kind == "unique"}
        self.system_fields = _system_fields_for(self.tenant_key, self.ttl_hours)
        self.system_field_map: Dict[str, FieldSchema] = {f.name: f for f in self.system_fields}

    def storage_fields(self) -> List[FieldSchema]:
        return [*self.fields, *self.system_fields]

    def _validate_schema(self) -> None:
        seen: set[str] = set()
        for f in self.fields:
            if f.name in seen:
                raise Namel3ssError(f"Duplicate field '{f.name}' in record '{self.name}'")
            if f.name in SYSTEM_FIELDS:
                raise Namel3ssError(f"Field '{f.name}' is reserved in record '{self.name}'")
            seen.add(f.name)
            if f.type_name not in SUPPORTED_TYPES:
                raise Namel3ssError(f"Unsupported field type '{f.type_name}' in record '{self.name}'")
            if (
                f.constraint
                and f.constraint.kind in {"gt", "gte", "lt", "lte", "len_min", "len_max"}
                and f.constraint.expression is None
            ):
                raise Namel3ssError(
                    f"Constraint '{f.constraint.kind}' requires an expression in record '{self.name}' field '{f.name}'"
                )
            if f.constraint and f.constraint.kind == "between":
                if f.constraint.expression is None or f.constraint.expression_high is None:
                    raise Namel3ssError(
                        f"Constraint 'between' requires two expressions in record '{self.name}' field '{f.name}'"
                    )
            if f.constraint and f.constraint.kind == "pattern" and not f.constraint.pattern:
                raise Namel3ssError(
                    f"Constraint 'pattern' requires a regex string in record '{self.name}' field '{f.name}'"
                )


def _system_fields_for(tenant_key: List[str] | None, ttl_hours: Decimal | None) -> List[FieldSchema]:
    fields: List[FieldSchema] = []
    if tenant_key:
        fields.append(FieldSchema(name=TENANT_KEY_FIELD, type_name="text", constraint=None))
    if ttl_hours is not None:
        fields.append(FieldSchema(name=EXPIRES_AT_FIELD, type_name="number", constraint=None))
    return fields
