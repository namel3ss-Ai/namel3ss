from __future__ import annotations

from namel3ss.foreign.types import normalize_foreign_type


def foreign_language_label(kind: str | None) -> str:
    normalized = (kind or "").strip().lower()
    if normalized == "node":
        return "js"
    if normalized == "javascript":
        return "js"
    if normalized == "python":
        return "python"
    return normalized or "unknown"


def build_foreign_functions_intent(program, *, policy_mode: str) -> list[dict] | None:
    tools = getattr(program, "tools", None)
    if not tools:
        return None
    foreign_tools = [tool for tool in tools.values() if getattr(tool, "declared_as", "tool") == "foreign"]
    if not foreign_tools:
        return None
    entries: list[dict] = []
    for tool in sorted(foreign_tools, key=lambda item: item.name):
        inputs = []
        for field in tool.input_fields:
            normalized, _ = normalize_foreign_type(field.type_name)
            inputs.append({"name": field.name, "type": normalized})
        output_type = None
        if tool.output_fields:
            output_type, _ = normalize_foreign_type(tool.output_fields[0].type_name)
        entries.append(
            {
                "name": tool.name,
                "language": foreign_language_label(getattr(tool, "kind", None)),
                "input_schema": inputs,
                "output_type": output_type,
                "policy_mode": policy_mode,
            }
        )
    return entries


__all__ = ["build_foreign_functions_intent", "foreign_language_label"]
