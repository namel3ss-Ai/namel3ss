from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir

SUPPORTED_TYPES = {"string", "int", "number", "boolean", "json"}


@dataclass
class FieldConstraint:
    kind: str  # present, unique, gt, lt, pattern, len_min, len_max
    expression: Optional[ir.Expression] = None
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

    def __post_init__(self) -> None:
        self._validate_schema()
        self.field_map: Dict[str, FieldSchema] = {f.name: f for f in self.fields}
        self.unique_fields = {f.name for f in self.fields if f.constraint and f.constraint.kind == "unique"}

    def _validate_schema(self) -> None:
        seen: set[str] = set()
        for f in self.fields:
            if f.name in seen:
                raise Namel3ssError(f"Duplicate field '{f.name}' in record '{self.name}'")
            seen.add(f.name)
            if f.type_name not in SUPPORTED_TYPES:
                raise Namel3ssError(f"Unsupported field type '{f.type_name}' in record '{self.name}'")
            if f.constraint and f.constraint.kind in {"gt", "lt", "len_min", "len_max"} and f.constraint.expression is None:
                raise Namel3ssError(
                    f"Constraint '{f.constraint.kind}' requires an expression in record '{self.name}' field '{f.name}'"
                )
            if f.constraint and f.constraint.kind == "pattern" and not f.constraint.pattern:
                raise Namel3ssError(
                    f"Constraint 'pattern' requires a regex string in record '{self.name}' field '{f.name}'"
                )

