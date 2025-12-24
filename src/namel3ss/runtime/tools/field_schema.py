from __future__ import annotations

from namel3ss.ir import nodes as ir


def build_json_schema(fields: list[ir.ToolField]) -> dict:
    properties: dict[str, dict[str, str]] = {}
    required: list[str] = []
    for field in fields:
        properties[field.name] = {"type": _json_type(field.type_name)}
        if field.required:
            required.append(field.name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _json_type(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw == "text":
        return "string"
    if raw == "number":
        return "number"
    if raw == "boolean":
        return "boolean"
    if raw == "json":
        return "object"
    return "string"


__all__ = ["build_json_schema"]
