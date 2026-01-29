from __future__ import annotations

import re
from typing import Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema


def field_to_ui(field: schema.FieldSchema) -> dict:
    return {
        "name": field.name,
        "label": label_from_identifier(field.name),
        "type": field.type_name,
        "constraints": constraints_to_ui(field.constraint),
    }


def constraints_to_ui(constraint: Optional[schema.FieldConstraint]) -> list[dict]:
    if constraint is None:
        return []
    kind = constraint.kind
    if kind == "present":
        return [{"kind": "present"}]
    if kind == "unique":
        return [{"kind": "unique"}]
    if kind == "pattern":
        return [{"kind": "pattern", "value": constraint.pattern}]
    if kind == "gt":
        return [{"kind": "greater_than", "value": _literal_value(constraint.expression)}]
    if kind == "gte":
        return [{"kind": "at_least", "value": _literal_value(constraint.expression)}]
    if kind == "lt":
        return [{"kind": "less_than", "value": _literal_value(constraint.expression)}]
    if kind == "lte":
        return [{"kind": "at_most", "value": _literal_value(constraint.expression)}]
    if kind == "between":
        return [
            {
                "kind": "between",
                "min": _literal_value(constraint.expression),
                "max": _literal_value(constraint.expression_high),
            }
        ]
    if kind == "int":
        return [{"kind": "integer"}]
    if kind == "len_min":
        return [{"kind": "length_min", "value": _literal_value(constraint.expression)}]
    if kind == "len_max":
        return [{"kind": "length_max", "value": _literal_value(constraint.expression)}]
    return []


def _literal_value(expr: ir.Expression | None) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if expr is None:
        return None
    raise Namel3ssError("Manifest requires literal constraint values")


_ACRONYMS: set[str] = {"id", "ip", "api", "url", "ui", "ai"}


def label_from_identifier(value: str) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", text)
    words = [word for word in text.split() if word]
    labeled: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered in _ACRONYMS:
            labeled.append(lowered.upper())
        else:
            labeled.append(word[:1].upper() + word[1:])
    return " ".join(labeled)


__all__ = ["field_to_ui", "constraints_to_ui", "label_from_identifier"]
