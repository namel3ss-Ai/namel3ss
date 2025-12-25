from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_capabilities_path


FILESYSTEM_LEVELS = {"none", "read", "write"}
NETWORK_LEVELS = {"none", "outbound"}
ENV_LEVELS = {"none", "read"}
SUBPROCESS_LEVELS = {"none", "allow"}
CAPABILITY_FIELDS = {"filesystem", "network", "env", "secrets", "subprocess"}


@dataclass(frozen=True)
class ToolCapabilities:
    filesystem: str
    network: str
    env: str
    subprocess: str
    secrets: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "filesystem": self.filesystem,
            "network": self.network,
            "env": self.env,
            "subprocess": self.subprocess,
            "secrets": list(self.secrets),
        }


def load_pack_capabilities(pack_dir: Path) -> dict[str, ToolCapabilities]:
    path = pack_capabilities_path(pack_dir)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return parse_capabilities_yaml(text, path)


def parse_capabilities_yaml(text: str, path: Path) -> dict[str, ToolCapabilities]:
    caps: dict[str, ToolCapabilities] = {}
    in_caps = False
    current_tool: str | None = None
    current_fields: dict[str, object] | None = None

    lines = text.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if not in_caps:
            if indent == 0 and stripped == "capabilities:":
                in_caps = True
                continue
            raise Namel3ssError(_invalid_capabilities_message(path))
        if indent == 0:
            raise Namel3ssError(_invalid_capabilities_message(path))
        if indent == 2:
            if current_tool and current_fields is not None:
                caps[current_tool] = _finalize_capability(current_tool, current_fields, path, line_no)
                current_tool = None
                current_fields = None
            if ":" not in stripped:
                raise Namel3ssError(_invalid_capabilities_message(path))
            key_part, value_part = stripped.split(":", 1)
            tool_name = _unquote(key_part.strip())
            if not tool_name:
                raise Namel3ssError(_invalid_capabilities_message(path))
            if value_part.strip():
                raise Namel3ssError(_invalid_capabilities_message(path))
            if tool_name in caps:
                raise Namel3ssError(_duplicate_tool_message(tool_name))
            current_tool = tool_name
            current_fields = {}
            continue
        if indent == 4:
            if not current_tool or current_fields is None:
                raise Namel3ssError(_invalid_capabilities_message(path))
            if ":" not in stripped:
                raise Namel3ssError(_invalid_capabilities_message(path))
            field_name, value_part = stripped.split(":", 1)
            key = field_name.strip()
            value = value_part.strip()
            if not key or value == "":
                raise Namel3ssError(_invalid_capabilities_message(path))
            if key not in CAPABILITY_FIELDS:
                raise Namel3ssError(_invalid_field_message(current_tool, key))
            if key in current_fields:
                raise Namel3ssError(_duplicate_field_message(current_tool, key))
            current_fields[key] = _parse_value(current_tool, key, value, path)
            continue
        raise Namel3ssError(_invalid_capabilities_message(path))

    if current_tool and current_fields is not None:
        caps[current_tool] = _finalize_capability(current_tool, current_fields, path, len(lines) + 1)

    if not in_caps:
        raise Namel3ssError(_invalid_capabilities_message(path))
    return caps


def capabilities_summary(capabilities: dict[str, ToolCapabilities]) -> dict[str, object]:
    levels = {
        "filesystem": _highest_level([cap.filesystem for cap in capabilities.values()], FILESYSTEM_LEVELS),
        "network": _highest_level([cap.network for cap in capabilities.values()], NETWORK_LEVELS),
        "env": _highest_level([cap.env for cap in capabilities.values()], ENV_LEVELS),
        "subprocess": _highest_level([cap.subprocess for cap in capabilities.values()], SUBPROCESS_LEVELS),
    }
    secrets: set[str] = set()
    for cap in capabilities.values():
        secrets.update(cap.secrets)
    return {"levels": levels, "secrets": sorted(secrets)}


def capabilities_by_tool(capabilities: dict[str, ToolCapabilities]) -> dict[str, dict[str, object]]:
    return {tool: cap.to_dict() for tool, cap in capabilities.items()}


def _finalize_capability(
    tool_name: str,
    fields: dict[str, object],
    path: Path,
    line_no: int,
) -> ToolCapabilities:
    missing = [field for field in ("filesystem", "network", "env", "subprocess") if field not in fields]
    if missing:
        raise Namel3ssError(_missing_fields_message(path, tool_name, missing, line_no))
    filesystem = _expect_level(tool_name, "filesystem", fields.get("filesystem"), FILESYSTEM_LEVELS)
    network = _expect_level(tool_name, "network", fields.get("network"), NETWORK_LEVELS)
    env = _expect_level(tool_name, "env", fields.get("env"), ENV_LEVELS)
    subprocess = _expect_level(tool_name, "subprocess", fields.get("subprocess"), SUBPROCESS_LEVELS)
    secrets = fields.get("secrets") or []
    if not isinstance(secrets, list) or any(not isinstance(item, str) or not item for item in secrets):
        raise Namel3ssError(_invalid_secrets_message(tool_name))
    return ToolCapabilities(
        filesystem=filesystem,
        network=network,
        env=env,
        subprocess=subprocess,
        secrets=sorted(dict.fromkeys(secrets)),
    )


def _expect_level(tool_name: str, field: str, value: object, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise Namel3ssError(_invalid_value_message(tool_name, field, allowed))
    return value


def _parse_value(tool_name: str, field: str, value: str, path: Path) -> object:
    _ = path
    if field == "secrets":
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as err:
            raise Namel3ssError(_invalid_secrets_message(tool_name)) from err
        return parsed
    return _unquote(value)


def _highest_level(values: list[str], allowed: set[str]) -> str:
    if not values:
        return "none"
    order = [level for level in ("none", "read", "write", "outbound", "allow") if level in allowed]
    level_map = {value: idx for idx, value in enumerate(order)}
    return max(values, key=lambda level: level_map.get(level, 0))


def _invalid_capabilities_message(path: Path) -> str:
    return build_guidance_message(
        what="Capabilities file is invalid.",
        why=f"Expected capabilities in {path.as_posix()}.",
        fix="Fix capabilities.yaml formatting.",
        example=_capabilities_example(),
    )


def _duplicate_tool_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f"Duplicate capabilities for '{tool_name}'.",
        why="Each tool can be declared only once.",
        fix="Remove the duplicate entry.",
        example=_capabilities_example(tool_name),
    )


def _invalid_field_message(tool_name: str, field: str) -> str:
    return build_guidance_message(
        what=f"Unsupported capability field '{field}' for '{tool_name}'.",
        why="Use filesystem, network, env, secrets, or subprocess.",
        fix="Replace the field with a supported capability.",
        example=_capabilities_example(tool_name),
    )


def _duplicate_field_message(tool_name: str, field: str) -> str:
    return build_guidance_message(
        what=f"Duplicate capability field '{field}' for '{tool_name}'.",
        why="Each capability field can be set only once.",
        fix="Remove the duplicate field.",
        example=_capabilities_example(tool_name),
    )


def _missing_fields_message(path: Path, tool_name: str, missing: list[str], line_no: int) -> str:
    return build_guidance_message(
        what=f"Capabilities for '{tool_name}' are incomplete.",
        why=f"Missing fields: {', '.join(missing)} (line {line_no}).",
        fix="Add the missing capability fields.",
        example=_capabilities_example(tool_name),
    )


def _invalid_value_message(tool_name: str, field: str, allowed: set[str]) -> str:
    return build_guidance_message(
        what=f"Capability '{field}' for '{tool_name}' is invalid.",
        why=f"Allowed values: {', '.join(sorted(allowed))}.",
        fix="Use a supported capability value.",
        example=_capabilities_example(tool_name),
    )


def _invalid_secrets_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f"Secrets list for '{tool_name}' is invalid.",
        why="Secrets must be a JSON array of strings.",
        fix="Provide a JSON list of secret names.",
        example=_capabilities_example(tool_name),
    )


def _capabilities_example(tool_name: str = "example tool") -> str:
    return (
        "capabilities:\n"
        f'  "{tool_name}":\n'
        '    filesystem: "read"\n'
        '    network: "outbound"\n'
        '    env: "read"\n'
        '    subprocess: "none"\n'
        '    secrets: ["API_KEY"]'
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


__all__ = [
    "CAPABILITY_FIELDS",
    "ENV_LEVELS",
    "FILESYSTEM_LEVELS",
    "NETWORK_LEVELS",
    "SUBPROCESS_LEVELS",
    "ToolCapabilities",
    "capabilities_by_tool",
    "capabilities_summary",
    "load_pack_capabilities",
    "parse_capabilities_yaml",
]
