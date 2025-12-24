from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


SUPPORTED_BINDING_KIND = "python"
SUPPORTED_PURITY = {"pure", "impure"}


@dataclass(frozen=True)
class ToolBinding:
    kind: str
    entry: str
    purity: str | None = None
    timeout_ms: int | None = None


def parse_bindings_yaml(text: str, path: Path) -> dict[str, ToolBinding]:
    bindings: dict[str, ToolBinding] = {}
    in_tools = False
    current_tool: str | None = None
    current_fields: dict[str, object] | None = None

    lines = text.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if not in_tools:
            if indent == 0 and stripped == "tools:":
                in_tools = True
                continue
            raise Namel3ssError(_invalid_bindings_message(path))
        if indent == 0:
            raise Namel3ssError(_invalid_bindings_message(path))
        if indent == 2:
            if current_tool and current_fields is not None:
                _finalize_binding(bindings, current_tool, current_fields, path, line_no)
                current_tool = None
                current_fields = None
            if ":" not in stripped:
                raise Namel3ssError(_invalid_bindings_message(path))
            key_part, value_part = stripped.split(":", 1)
            tool_name = _unquote(key_part.strip())
            if not tool_name:
                raise Namel3ssError(_invalid_bindings_message(path))
            value = value_part.strip()
            if value:
                entry = _unquote(value)
                _add_binding(bindings, tool_name, ToolBinding(kind=SUPPORTED_BINDING_KIND, entry=entry), path, line_no)
            else:
                if tool_name in bindings:
                    raise Namel3ssError(_duplicate_tool_message(tool_name))
                current_tool = tool_name
                current_fields = {}
            continue
        if indent == 4:
            if not current_tool or current_fields is None:
                raise Namel3ssError(_invalid_bindings_message(path))
            if ":" not in stripped:
                raise Namel3ssError(_invalid_bindings_message(path))
            field_name, value_part = stripped.split(":", 1)
            key = field_name.strip()
            value = value_part.strip()
            if not key or not value:
                raise Namel3ssError(_invalid_bindings_message(path))
            if key in current_fields:
                raise Namel3ssError(_duplicate_field_message(current_tool, key))
            if key not in {"kind", "entry", "purity", "timeout_ms"}:
                raise Namel3ssError(_invalid_field_message(current_tool, key))
            current_fields[key] = _parse_value(key, value, path)
            continue
        raise Namel3ssError(_invalid_bindings_message(path))

    if current_tool and current_fields is not None:
        _finalize_binding(bindings, current_tool, current_fields, path, len(lines) + 1)

    if not in_tools:
        raise Namel3ssError(_invalid_bindings_message(path))
    return bindings


def render_bindings_yaml(bindings: dict[str, ToolBinding]) -> str:
    lines = ["tools:"]
    for name in sorted(bindings):
        binding = bindings[name]
        lines.append(f"  {_quote(name)}:")
        lines.append(f"    kind: {_quote(binding.kind)}")
        lines.append(f"    entry: {_quote(binding.entry)}")
        if binding.purity is not None:
            lines.append(f"    purity: {_quote(binding.purity)}")
        if binding.timeout_ms is not None:
            lines.append(f"    timeout_ms: {binding.timeout_ms}")
    return "\n".join(lines) + "\n"


def _finalize_binding(
    bindings: dict[str, ToolBinding],
    tool_name: str,
    fields: dict[str, object],
    path: Path,
    line_no: int,
) -> None:
    kind = fields.get("kind")
    entry = fields.get("entry")
    if not isinstance(kind, str) or not kind:
        raise Namel3ssError(_missing_field_message(path, tool_name, "kind", line_no))
    if kind != SUPPORTED_BINDING_KIND:
        raise Namel3ssError(_invalid_kind_message(path, tool_name, kind))
    if not isinstance(entry, str) or not entry:
        raise Namel3ssError(_missing_field_message(path, tool_name, "entry", line_no))
    purity = fields.get("purity")
    if purity is not None and (not isinstance(purity, str) or purity not in SUPPORTED_PURITY):
        raise Namel3ssError(_invalid_purity_message(path, tool_name))
    timeout_ms = fields.get("timeout_ms")
    if timeout_ms is not None and (not isinstance(timeout_ms, int) or timeout_ms <= 0):
        raise Namel3ssError(_invalid_timeout_message(path, tool_name))
    _add_binding(
        bindings,
        tool_name,
        ToolBinding(kind=kind, entry=entry, purity=purity, timeout_ms=timeout_ms),
        path,
        line_no,
    )


def _parse_value(key: str, value: str, path: Path) -> object:
    if key == "timeout_ms":
        try:
            parsed = int(value)
        except ValueError:
            raise Namel3ssError(_invalid_timeout_message(path, "<unknown>"))
        return parsed
    return _unquote(value)


def _add_binding(
    bindings: dict[str, ToolBinding],
    tool_name: str,
    binding: ToolBinding,
    path: Path,
    line_no: int,
) -> None:
    if tool_name in bindings:
        raise Namel3ssError(_duplicate_tool_message(tool_name))
    if not binding.entry:
        raise Namel3ssError(_invalid_bindings_message(path))
    bindings[tool_name] = binding


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _unquote(value: str) -> str:
    if len(value) >= 2 and ((value[0] == value[-1]) and value[0] in {'"', "'"}):
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def _invalid_bindings_message(path: Path) -> str:
    return build_guidance_message(
        what="Tool bindings file is invalid.",
        why=f"Expected a tools: mapping in {path.as_posix()}.",
        fix="Rewrite the bindings file or regenerate it with n3 tools bind.",
        example=_bindings_example("get data from a web address"),
    )


def _duplicate_tool_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f"Duplicate tool binding for '{tool_name}'.",
        why="Each tool can only be bound once.",
        fix="Remove the duplicate entry.",
        example=_bindings_example(tool_name),
    )


def _duplicate_field_message(tool_name: str, field_name: str) -> str:
    return build_guidance_message(
        what=f"Duplicate '{field_name}' field for '{tool_name}'.",
        why="Each binding field must be unique.",
        fix="Remove the duplicate field.",
        example=_bindings_example(tool_name),
    )


def _invalid_field_message(tool_name: str, field_name: str) -> str:
    return build_guidance_message(
        what=f"Unsupported binding field '{field_name}' for '{tool_name}'.",
        why="Bindings only support kind, entry, purity, and timeout_ms.",
        fix="Remove the unsupported field.",
        example=_bindings_example(tool_name),
    )


def _missing_field_message(path: Path, tool_name: str, field_name: str, line_no: int) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' is missing '{field_name}'.",
        why=f"The binding entry is incomplete near line {line_no}.",
        fix="Add the missing field.",
        example=_bindings_example(tool_name),
    )


def _invalid_kind_message(path: Path, tool_name: str, kind: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid kind '{kind}'.",
        why=f"Only '{SUPPORTED_BINDING_KIND}' bindings are supported.",
        fix="Set kind to 'python'.",
        example=_bindings_example(tool_name),
    )


def _invalid_purity_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid purity.",
        why="purity must be 'pure' or 'impure'.",
        fix="Update purity or remove the field.",
        example=_bindings_example(tool_name),
    )


def _invalid_timeout_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid timeout_ms.",
        why="timeout_ms must be a positive integer.",
        fix="Update timeout_ms or remove the field.",
        example=_bindings_example(tool_name),
    )


def _bindings_example(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "tools.my_tool:run"'
    )


__all__ = ["ToolBinding", "parse_bindings_yaml", "render_bindings_yaml"]
