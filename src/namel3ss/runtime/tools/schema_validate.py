from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.foreign.types import (
    foreign_type_suggestions,
    foreign_value_matches,
    foreign_value_type,
    is_foreign_type,
    normalize_foreign_type,
)
from namel3ss.ir import nodes as ir
from namel3ss.utils.numbers import is_number


_SUPPORTED_TYPES = {"text", "number", "boolean", "json"}


def validate_tool_fields(
    *,
    fields: list[ir.ToolField],
    payload: object,
    tool_name: str,
    phase: str,
    line: int | None,
    column: int | None,
    type_mode: str = "tool",
    expect_object: bool = True,
) -> None:
    if type_mode == "foreign":
        _validate_foreign_fields(
            fields=fields,
            payload=payload,
            tool_name=tool_name,
            phase=phase,
            line=line,
            column=column,
            expect_object=expect_object,
        )
        return
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Tool {phase} for \"{tool_name}\" must be a JSON object.",
                why=f"The {phase} value is {_value_kind(payload)}, but fields require an object.",
                fix=f"Return a JSON object for tool {phase}.",
                example=_tool_payload_example(tool_name, phase, fields),
            ),
            line=line,
            column=column,
        )
    field_map = {field.name: field for field in fields}
    for key in payload:
        if key not in field_map:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Tool {phase} for \"{tool_name}\" has unknown field \"{key}\".",
                    why="The field is not declared in the tool schema.",
                    fix="Remove the field or add it to the tool declaration.",
                    example=_tool_payload_example(tool_name, phase, fields),
                ),
                line=line,
                column=column,
            )
    for field in fields:
        if field.required and field.name not in payload:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Tool {phase} for \"{tool_name}\" is missing required field \"{field.name}\".",
                    why=f"The tool declares \"{field.name}\" as {field.type_name}.",
                    fix="Add the field to the tool payload or mark it optional.",
                    example=_tool_payload_example(tool_name, phase, fields, highlight=field),
                ),
                line=line,
                column=column,
            )
    for field in fields:
        if field.name not in payload:
            continue
        expected = _normalize_type(field.type_name, tool_name, phase, line, column)
        if not _value_matches_type(payload[field.name], expected):
            actual = _value_kind(payload[field.name])
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Tool {phase} field \"{field.name}\" must be {expected}.",
                    why=f"The value is {actual}, but the tool declares {expected}.",
                    fix=f"Provide a {expected} value for \"{field.name}\".",
                    example=_tool_payload_example(tool_name, phase, fields, highlight=field),
                ),
                line=line,
                column=column,
            )


def _normalize_type(value: str, tool_name: str, phase: str, line: int | None, column: int | None) -> str:
    raw = value.strip().lower()
    if raw not in _SUPPORTED_TYPES:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Tool \"{tool_name}\" uses unsupported {phase} type \"{value}\".",
                why="Only text, number, boolean, and json are supported.",
                fix="Update the tool declaration to use a supported type.",
                example=_tool_payload_example(tool_name, phase, []),
            ),
            line=line,
            column=column,
        )
    return raw


def _value_matches_type(value: object, expected: str) -> bool:
    if expected == "text":
        return isinstance(value, str)
    if expected == "number":
        return is_number(value)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "json":
        return isinstance(value, (dict, list))
    return False


def _value_kind(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def _validate_foreign_fields(
    *,
    fields: list[ir.ToolField],
    payload: object,
    tool_name: str,
    phase: str,
    line: int | None,
    column: int | None,
    expect_object: bool,
) -> None:
    if not expect_object:
        if len(fields) != 1:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign function "{tool_name}" output schema is invalid.',
                    why="Foreign outputs must declare a single type.",
                    fix="Declare a single output type in the foreign function.",
                    example=_foreign_decl_example(tool_name),
                ),
                line=line,
                column=column,
            )
        expected_raw = fields[0].type_name
        expected = _normalize_foreign_type(expected_raw, tool_name, phase, line, column)
        if not foreign_value_matches(payload, expected):
            actual = foreign_value_type(payload)
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign output for "{tool_name}" must be {expected}.',
                    why=f"The value is {actual}, but the foreign function declares {expected}.",
                    fix=f"Return a {expected} value from the foreign function.",
                    example=_foreign_output_example(expected),
                ),
                line=line,
                column=column,
            )
        return
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign {phase} for "{tool_name}" must be a JSON object.',
                why=f"The {phase} value is {_value_kind(payload)}, but inputs require an object.",
                fix=f"Provide a JSON object for foreign {phase}.",
                example=_foreign_input_example(tool_name, fields),
            ),
            line=line,
            column=column,
        )
    field_map = {field.name: field for field in fields}
    for key in payload:
        if key not in field_map:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign {phase} for "{tool_name}" has unknown field "{key}".',
                    why="The field is not declared in the foreign input schema.",
                    fix="Remove the field or add it to the foreign declaration.",
                    example=_foreign_input_example(tool_name, fields),
                ),
                line=line,
                column=column,
            )
    for field in fields:
        if field.required and field.name not in payload:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign {phase} for "{tool_name}" is missing required field "{field.name}".',
                    why=f'The foreign declaration expects "{field.name}" as {field.type_name}.',
                    fix="Add the field to the foreign call.",
                    example=_foreign_input_example(tool_name, fields, highlight=field),
                ),
                line=line,
                column=column,
            )
    for field in fields:
        if field.name not in payload:
            continue
        expected = _normalize_foreign_type(field.type_name, tool_name, phase, line, column)
        if not foreign_value_matches(payload[field.name], expected):
            actual = foreign_value_type(payload[field.name])
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign {phase} field "{field.name}" must be {expected}.',
                    why=f"The value is {actual}, but the foreign declaration expects {expected}.",
                    fix=f"Provide a {expected} value for \"{field.name}\".",
                    example=_foreign_input_example(tool_name, fields, highlight=field),
                ),
                line=line,
                column=column,
            )


def _normalize_foreign_type(
    value: str,
    tool_name: str,
    phase: str,
    line: int | None,
    column: int | None,
) -> str:
    normalized, _ = normalize_foreign_type(value)
    if not is_foreign_type(normalized):
        suggestions = foreign_type_suggestions(value)
        hint = f" Did you mean '{suggestions[0]}'?" if suggestions else ""
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign function "{tool_name}" uses unsupported {phase} type "{value}".{hint}',
                why="Foreign types must be text, number, boolean, or list of those types.",
                fix="Update the foreign declaration to a supported type.",
                example=_foreign_decl_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return normalized


def _tool_payload_example(
    tool_name: str,
    phase: str,
    fields: list[ir.ToolField],
    *,
    highlight: ir.ToolField | None = None,
) -> str:
    if not fields:
        return (
            f'let result is {tool_name}:\n'
            "  # add fields here\n\n"
            "# tool output should return a JSON object"
        )
    lines = [f"let result is {tool_name}:"] if phase == "input" else ["return {"]
    for field in fields:
        sample = _sample_value(field.type_name)
        if phase == "input":
            line = f"  {field.name} is {sample}"
        else:
            line = f'  "{field.name}": {sample},'
        if highlight and field.name == highlight.name:
            line = f"{line}  # required"
        lines.append(line)
    if phase == "output":
        lines.append("}")
    return "\n".join(lines)


def _sample_value(field_type: str) -> str:
    if field_type == "text":
        return '"value"'
    if field_type == "number":
        return "1"
    if field_type == "boolean":
        return "true"
    return "{}"


def _foreign_input_example(
    tool_name: str,
    fields: list[ir.ToolField],
    *,
    highlight: ir.ToolField | None = None,
) -> str:
    lines = [f'call foreign "{tool_name}"']
    for field in fields:
        sample = _foreign_sample_value(field.type_name)
        line = f"  {field.name} is {sample}"
        if highlight and field.name == highlight.name:
            line = f"{line}  # required"
        lines.append(line)
    return "\n".join(lines)


def _foreign_output_example(expected: str) -> str:
    return f"return {_foreign_sample_value(expected)}"


def _foreign_sample_value(field_type: str) -> str:
    if field_type.startswith("list of "):
        item_type = field_type[len("list of "):].strip()
        return f"[{_foreign_sample_value(item_type)}]"
    if field_type == "text":
        return '"value"'
    if field_type == "number":
        return "1"
    if field_type == "boolean":
        return "true"
    return '"value"'


def _foreign_decl_example(tool_name: str) -> str:
    return (
        f'foreign python function "{tool_name}"\n'
        "  input\n"
        "    amount is number\n"
        "  output is number"
    )


__all__ = ["validate_tool_fields"]
