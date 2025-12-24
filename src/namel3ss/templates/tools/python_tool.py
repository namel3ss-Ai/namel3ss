from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_FIELD_TYPES = {"text", "number", "boolean", "json"}


@dataclass(frozen=True)
class ToolField:
    name: str
    field_type: str
    required: bool = True


def render_tool_module(
    *,
    tool_name: str,
    function_name: str,
    input_fields: list[ToolField],
    output_fields: list[ToolField],
) -> str:
    input_lines = _render_schema_comments("Input schema", input_fields)
    output_lines = _render_schema_comments("Output schema", output_fields)
    body_lines = [
        f"def {function_name}(payload: dict) -> dict:",
        f'    """Generated tool: {tool_name}."""',
        *input_lines,
        *output_lines,
    ]
    body_lines.extend(_render_return_block(output_fields))
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "",
            *body_lines,
            "",
        ]
    )


def render_tool_decl(
    *,
    tool_name: str,
    purity: str,
    timeout_seconds: int | None,
    input_fields: list[ToolField],
    output_fields: list[ToolField],
) -> str:
    lines = [
        f'tool "{tool_name}":',
        "  implemented using python",
        f'  purity is "{purity}"',
    ]
    if timeout_seconds is not None:
        lines.append(f"  timeout_seconds is {timeout_seconds}")
    lines.append("")
    lines.append("  input:")
    lines.extend(_render_field_lines(input_fields, indent="    "))
    lines.append("")
    lines.append("  output:")
    lines.extend(_render_field_lines(output_fields, indent="    "))
    return "\n".join(lines)


def _render_field_lines(fields: list[ToolField], *, indent: str) -> list[str]:
    if not fields:
        return []
    lines: list[str] = []
    for field in _ordered_fields(fields):
        optional = "optional " if not field.required else ""
        lines.append(f"{indent}{field.name} is {optional}{field.field_type}")
    return lines


def _ordered_fields(fields: list[ToolField]) -> list[ToolField]:
    normalized = [
        ToolField(name=field.name, field_type=field.field_type, required=field.required) for field in fields
    ]
    return sorted(normalized, key=lambda field: field.name)


def _render_schema_comments(label: str, fields: list[ToolField]) -> list[str]:
    lines = [f"    # {label}:"]
    if not fields:
        lines.append("    # - (none)")
        return lines
    for field in _ordered_fields(fields):
        required = "required" if field.required else "optional"
        lines.append(f"    # - {field.name}: {field.field_type} ({required})")
    return lines


def _render_return_block(fields: list[ToolField]) -> list[str]:
    if not fields:
        return ["    return {}"]
    lines = ["    return {"]
    for field in _ordered_fields(fields):
        lines.append(f'        "{field.name}": {_default_for_type(field.field_type)},')
    lines.append("    }")
    return lines


def _default_for_type(field_type: str) -> str:
    if field_type == "text":
        return '""'
    if field_type == "number":
        return "0"
    if field_type == "boolean":
        return "False"
    return "{}"


__all__ = ["SUPPORTED_FIELD_TYPES", "ToolField", "render_tool_decl", "render_tool_module"]
