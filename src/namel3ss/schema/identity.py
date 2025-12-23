from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import FieldSchema, SUPPORTED_TYPES


@dataclass
class IdentitySchema:
    name: str
    fields: List[FieldSchema] = field(default_factory=list)
    trust_levels: List[str] | None = None
    line: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        self._validate_schema()
        self.field_map: Dict[str, FieldSchema] = {f.name: f for f in self.fields}

    def _validate_schema(self) -> None:
        seen: set[str] = set()
        for f in self.fields:
            if f.name in seen:
                raise Namel3ssError(f"Duplicate identity field '{f.name}' in identity '{self.name}'")
            seen.add(f.name)
            if f.type_name not in SUPPORTED_TYPES:
                raise Namel3ssError(f"Unsupported identity field type '{f.type_name}' in identity '{self.name}'")
