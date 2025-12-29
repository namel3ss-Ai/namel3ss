from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


SUPPORTED_BINDING_KINDS = {"python", "node"}
SUPPORTED_PURITY = {"pure", "impure"}
SUPPORTED_RUNNERS = {"local", "service", "container", "node"}
SUPPORTED_ENFORCEMENT = {"declared", "verified"}


@dataclass(frozen=True)
class ToolBinding:
    kind: str
    entry: str
    runner: str | None = None
    url: str | None = None
    image: str | None = None
    command: list[str] | None = None
    env: dict[str, str] | None = None
    purity: str | None = None
    timeout_ms: int | None = None
    sandbox: bool | None = None
    enforcement: str | None = None


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
                raise Namel3ssError(_inline_binding_message(tool_name))
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
            if key not in {
                "kind",
                "entry",
                "runner",
                "url",
                "image",
                "command",
                "env",
                "purity",
                "timeout_ms",
                "sandbox",
                "enforcement",
            }:
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
        if binding.runner is not None:
            lines.append(f"    runner: {_quote(binding.runner)}")
        if binding.url is not None:
            lines.append(f"    url: {_quote(binding.url)}")
        if binding.image is not None:
            lines.append(f"    image: {_quote(binding.image)}")
        if binding.command is not None:
            lines.append(f"    command: {json.dumps(binding.command)}")
        if binding.env is not None:
            lines.append(f"    env: {json.dumps(binding.env, sort_keys=True)}")
        if binding.purity is not None:
            lines.append(f"    purity: {_quote(binding.purity)}")
        if binding.timeout_ms is not None:
            lines.append(f"    timeout_ms: {binding.timeout_ms}")
        if binding.sandbox is not None:
            lines.append(f"    sandbox: {'true' if binding.sandbox else 'false'}")
        if binding.enforcement is not None:
            lines.append(f"    enforcement: {_quote(binding.enforcement)}")
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
    if kind not in SUPPORTED_BINDING_KINDS:
        raise Namel3ssError(_invalid_kind_message(path, tool_name, kind))
    if not isinstance(entry, str) or not entry:
        raise Namel3ssError(_missing_field_message(path, tool_name, "entry", line_no))
    runner = fields.get("runner")
    if runner is not None and (not isinstance(runner, str) or not runner):
        raise Namel3ssError(_invalid_runner_message(path, tool_name))
    url = fields.get("url")
    if url is not None and (not isinstance(url, str) or not url):
        raise Namel3ssError(_invalid_url_message(path, tool_name))
    image = fields.get("image")
    if image is not None and (not isinstance(image, str) or not image):
        raise Namel3ssError(_invalid_image_message(path, tool_name))
    command = fields.get("command")
    if command is not None:
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise Namel3ssError(_invalid_command_message(path, tool_name))
    env = fields.get("env")
    if env is not None:
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            raise Namel3ssError(_invalid_env_message(path, tool_name))
    purity = fields.get("purity")
    if purity is not None and (not isinstance(purity, str) or purity not in SUPPORTED_PURITY):
        raise Namel3ssError(_invalid_purity_message(path, tool_name))
    timeout_ms = fields.get("timeout_ms")
    if timeout_ms is not None and (not isinstance(timeout_ms, int) or timeout_ms <= 0):
        raise Namel3ssError(_invalid_timeout_message(path, tool_name))
    sandbox = fields.get("sandbox")
    if sandbox is not None and not isinstance(sandbox, bool):
        raise Namel3ssError(_invalid_sandbox_message(path, tool_name))
    enforcement = fields.get("enforcement")
    if enforcement is not None and (not isinstance(enforcement, str) or enforcement not in SUPPORTED_ENFORCEMENT):
        raise Namel3ssError(_invalid_enforcement_message(path, tool_name))
    _add_binding(
        bindings,
        tool_name,
        ToolBinding(
            kind=kind,
            entry=entry,
            runner=runner,
            url=url,
            image=image,
            command=command,
            env=env,
            purity=purity,
            timeout_ms=timeout_ms,
            sandbox=sandbox,
            enforcement=enforcement,
        ),
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
    if key == "sandbox":
        return _parse_bool(value, path)
    if key in {"command", "env"}:
        return _parse_inline_json(value, path)
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
        why=(
            "Bindings only support kind, entry, runner, url, image, command, env, purity, "
            "timeout_ms, sandbox, and enforcement."
        ),
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
        why=f"Supported kinds are: {', '.join(sorted(SUPPORTED_BINDING_KINDS))}.",
        fix="Set kind to a supported value.",
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


def _invalid_sandbox_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid sandbox value.",
        why=f"Sandbox must be true or false in {path.as_posix()}.",
        fix="Set sandbox to true or false.",
        example="sandbox: true",
    )


def _invalid_enforcement_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid enforcement value.",
        why=f"Enforcement must be declared or verified in {path.as_posix()}.",
        fix="Set enforcement to declared or verified.",
        example='enforcement: "verified"',
    )


def _bindings_example(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "tools.my_tool:run"'
    )


def _invalid_runner_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid runner.",
        why=f"runner must be one of: {', '.join(sorted(SUPPORTED_RUNNERS))}.",
        fix="Update runner or remove the field.",
        example=_bindings_example(tool_name),
    )


def _invalid_url_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid url.",
        why="url must be a non-empty string.",
        fix="Update url or remove the field.",
        example=_bindings_example(tool_name),
    )


def _invalid_image_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid image.",
        why="image must be a non-empty string.",
        fix="Update image or remove the field.",
        example=_bindings_example(tool_name),
    )


def _invalid_command_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid command.",
        why="command must be an array of strings.",
        fix="Update command to an inline JSON array.",
        example='command: ["python", "-m", "namel3ss_tools.runner"]',
    )


def _invalid_env_message(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' has invalid env.",
        why="env must be a mapping of string keys to string values.",
        fix="Update env to an inline JSON object.",
        example='env: {"LOG_LEVEL": "info"}',
    )


def _parse_inline_json(value: str, path: Path) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Inline JSON in tools.yaml is invalid.",
                why=str(err),
                fix="Use a JSON array/object inline.",
                example='command: ["python", "-m", "namel3ss_tools.runner"]',
            )
        ) from err


def _parse_bool(value: str, path: Path) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    raise Namel3ssError(
        build_guidance_message(
            what="Tool bindings file is invalid.",
            why=f"Expected true or false for sandbox in {path.as_posix()}.",
            fix="Set sandbox to true or false.",
            example="sandbox: false",
        )
    )


def _inline_binding_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f"Tool binding '{tool_name}' must be an object.",
        why="Inline string bindings are no longer supported.",
        fix="Use a mapping with kind and entry fields.",
        example=_bindings_example(tool_name),
    )


__all__ = ["ToolBinding", "parse_bindings_yaml", "render_bindings_yaml"]
