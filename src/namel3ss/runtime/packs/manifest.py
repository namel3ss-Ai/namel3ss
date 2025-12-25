from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, SUPPORTED_PURITY
from namel3ss.runtime.tools.runners.registry import list_runners


SUPPORTED_KIND = "python"


@dataclass(frozen=True)
class PackManifest:
    pack_id: str
    name: str
    version: str
    description: str
    author: str
    license: str
    tools: list[str]
    runners_default: str | None = None
    service_url: str | None = None
    container_image: str | None = None
    entrypoints: dict[str, ToolBinding] | None = None
    signer_id: str | None = None
    signed_at: str | None = None
    digest: str | None = None


def parse_pack_manifest(path: Path) -> PackManifest:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Unable to read pack manifest.",
                why=str(err),
                fix="Ensure pack.yaml is readable.",
                example="pack.yaml",
            )
        ) from err
    return parse_pack_manifest_text(text, path)


def parse_pack_manifest_text(text: str, path: Path) -> PackManifest:
    data = _parse_manifest(text, path)
    missing = [key for key in ["id", "name", "version", "description", "author", "license", "tools"] if key not in data]
    if missing:
        raise Namel3ssError(_missing_manifest_fields(path, missing))
    tools = data["tools"]
    if not isinstance(tools, list) or any(not isinstance(item, str) or not item for item in tools):
        raise Namel3ssError(_invalid_tools_list(path))
    runners_default = _string_or_none(data.get("runners_default"))
    if runners_default is not None and runners_default not in list_runners():
        raise Namel3ssError(_invalid_runner(path, runners_default))
    entrypoints = _parse_entrypoints(data.get("entrypoints"), path)
    return PackManifest(
        pack_id=str(data["id"]),
        name=str(data["name"]),
        version=str(data["version"]),
        description=str(data["description"]),
        author=str(data["author"]),
        license=str(data["license"]),
        tools=tools,
        runners_default=runners_default,
        service_url=_string_or_none(data.get("service_url")),
        container_image=_string_or_none(data.get("container_image")),
        entrypoints=entrypoints,
        signer_id=_string_or_none(data.get("signer_id")),
        signed_at=_string_or_none(data.get("signed_at")),
        digest=_string_or_none(data.get("digest")),
    )


def _parse_manifest(text: str, path: Path) -> dict:
    lines = text.splitlines()
    data: dict[str, object] = {}
    idx = 0
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        idx += 1
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent != 0 or ":" not in stripped:
            raise Namel3ssError(_invalid_manifest(path))
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {
            "id",
            "name",
            "version",
            "description",
            "author",
            "license",
            "service_url",
            "signer_id",
            "signed_at",
            "digest",
        }:
            if not value:
                raise Namel3ssError(_invalid_manifest(path))
            data[key] = _unquote(value)
            continue
        if key == "tools":
            if value:
                raise Namel3ssError(_invalid_manifest(path))
            tool_list, idx = _parse_list(lines, idx, path)
            data[key] = tool_list
            continue
        if key == "runners":
            if value:
                raise Namel3ssError(_invalid_manifest(path))
            mapping, idx = _parse_mapping(lines, idx, path)
            data["runners_default"] = mapping.get("default")
            continue
        if key == "container":
            if value:
                raise Namel3ssError(_invalid_manifest(path))
            mapping, idx = _parse_mapping(lines, idx, path)
            data["container_image"] = mapping.get("image")
            continue
        if key == "entrypoints":
            if value:
                raise Namel3ssError(_invalid_manifest(path))
            entrypoints, idx = _parse_entrypoints_block(lines, idx, path)
            data["entrypoints"] = entrypoints
            continue
        raise Namel3ssError(_invalid_manifest(path))
    return data


def _parse_list(lines: list[str], idx: int, path: Path) -> tuple[list[str], int]:
    items: list[str] = []
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            break
        if indent != 2 or not stripped.startswith("- "):
            raise Namel3ssError(_invalid_manifest(path))
        value = stripped[2:].strip()
        if not value:
            raise Namel3ssError(_invalid_manifest(path))
        items.append(_unquote(value))
        idx += 1
    return items, idx


def _parse_mapping(lines: list[str], idx: int, path: Path) -> tuple[dict[str, str], int]:
    mapping: dict[str, str] = {}
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            break
        if indent != 2 or ":" not in stripped:
            raise Namel3ssError(_invalid_manifest(path))
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise Namel3ssError(_invalid_manifest(path))
        mapping[key] = _unquote(value)
        idx += 1
    return mapping, idx


def _parse_entrypoints_block(lines: list[str], idx: int, path: Path) -> tuple[dict[str, dict], int]:
    entrypoints: dict[str, dict] = {}
    current_tool: str | None = None
    current_fields: dict[str, object] | None = None
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            break
        if indent == 2:
            if current_tool and current_fields is not None:
                entrypoints[current_tool] = current_fields
                current_tool = None
                current_fields = None
            if ":" not in stripped:
                raise Namel3ssError(_invalid_manifest(path))
            key_part, value_part = stripped.split(":", 1)
            tool_name = _unquote(key_part.strip())
            if not tool_name:
                raise Namel3ssError(_invalid_manifest(path))
            if value_part.strip():
                raise Namel3ssError(_invalid_manifest(path))
            current_tool = tool_name
            current_fields = {}
            idx += 1
            continue
        if indent == 4:
            if current_tool is None or current_fields is None:
                raise Namel3ssError(_invalid_manifest(path))
            if ":" not in stripped:
                raise Namel3ssError(_invalid_manifest(path))
            field_name, value_part = stripped.split(":", 1)
            key = field_name.strip()
            value = value_part.strip()
            if not key or not value:
                raise Namel3ssError(_invalid_manifest(path))
            current_fields[key] = _unquote(value)
            idx += 1
            continue
        raise Namel3ssError(_invalid_manifest(path))
    if current_tool and current_fields is not None:
        entrypoints[current_tool] = current_fields
    return entrypoints, idx


def _parse_entrypoints(raw: object, path: Path) -> dict[str, ToolBinding] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise Namel3ssError(_invalid_manifest(path))
    entrypoints: dict[str, ToolBinding] = {}
    for tool_name, fields in raw.items():
        if not isinstance(tool_name, str) or not tool_name:
            raise Namel3ssError(_invalid_manifest(path))
        if not isinstance(fields, dict):
            raise Namel3ssError(_invalid_manifest(path))
        kind = fields.get("kind")
        entry = fields.get("entry")
        runner = fields.get("runner")
        purity = fields.get("purity")
        timeout = fields.get("timeout_ms")
        if kind is None:
            kind = SUPPORTED_KIND
        if kind != SUPPORTED_KIND:
            raise Namel3ssError(_invalid_entry_kind(path, tool_name))
        if not isinstance(entry, str) or not entry:
            raise Namel3ssError(_invalid_entry_missing(path, tool_name))
        if runner is not None and (not isinstance(runner, str) or not runner):
            raise Namel3ssError(_invalid_entry_runner(path, tool_name))
        if purity is not None and (not isinstance(purity, str) or purity not in SUPPORTED_PURITY):
            raise Namel3ssError(_invalid_entry_purity(path, tool_name))
        timeout_ms = None
        if timeout is not None:
            try:
                timeout_ms = int(timeout)
            except (TypeError, ValueError) as err:
                raise Namel3ssError(_invalid_entry_timeout(path, tool_name)) from err
            if timeout_ms <= 0:
                raise Namel3ssError(_invalid_entry_timeout(path, tool_name))
        entrypoints[tool_name] = ToolBinding(
            kind=str(kind),
            entry=entry,
            runner=runner,
            purity=purity,
            timeout_ms=timeout_ms,
        )
    return entrypoints


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        return None
    return value


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def _invalid_manifest(path: Path) -> str:
    return build_guidance_message(
        what="Pack manifest is invalid.",
        why=f"Expected a valid pack.yaml in {path.as_posix()}.",
        fix="Fix pack.yaml or regenerate the pack manifest.",
        example=_manifest_example(),
    )


def _missing_manifest_fields(path: Path, missing: list[str]) -> str:
    return build_guidance_message(
        what="Pack manifest is missing required fields.",
        why=f"Missing fields: {', '.join(missing)}.",
        fix="Add the missing fields to pack.yaml.",
        example=_manifest_example(),
    )


def _invalid_tools_list(path: Path) -> str:
    return build_guidance_message(
        what="Pack manifest tools list is invalid.",
        why="tools must be a list of English tool names.",
        fix="Update the tools list to include tool names.",
        example='tools:\\n  - "greet someone"',
    )


def _invalid_runner(path: Path, runner: str) -> str:
    return build_guidance_message(
        what="Pack manifest runner default is invalid.",
        why=f"Runner '{runner}' is not supported.",
        fix="Use local, service, or container.",
        example='runners:\\n  default: "local"',
    )


def _invalid_entry_kind(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Pack entrypoint '{tool_name}' has invalid kind.",
        why="Only python tool entrypoints are supported.",
        fix="Set kind to python.",
        example=f'entrypoints:\\n  "{tool_name}":\\n    kind: "python"\\n    entry: "tools.my_tool:run"',
    )


def _invalid_entry_missing(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Pack entrypoint '{tool_name}' is missing entry.",
        why="Entrypoints must include a module:function entry.",
        fix="Add an entry field.",
        example=f'entrypoints:\\n  "{tool_name}":\\n    entry: "tools.my_tool:run"',
    )


def _invalid_entry_runner(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Pack entrypoint '{tool_name}' has invalid runner.",
        why="Runner must be local, service, or container.",
        fix="Update runner or remove it.",
        example='runner: "local"',
    )


def _invalid_entry_purity(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Pack entrypoint '{tool_name}' has invalid purity.",
        why="Purity must be pure or impure.",
        fix="Update purity or remove it.",
        example='purity: "impure"',
    )


def _invalid_entry_timeout(path: Path, tool_name: str) -> str:
    return build_guidance_message(
        what=f"Pack entrypoint '{tool_name}' has invalid timeout_ms.",
        why="timeout_ms must be a positive integer.",
        fix="Update timeout_ms or remove it.",
        example="timeout_ms: 10000",
    )


def _manifest_example() -> str:
    return (
        'id: "pack.slug"\\n'
        'name: "Sample Pack"\\n'
        'version: "0.1.0"\\n'
        'description: "Example pack"\\n'
        'author: "Team"\\n'
        'license: "MIT"\\n'
        "tools:\\n"
        '  - "greet someone"'
    )


__all__ = ["PackManifest", "parse_pack_manifest"]
