from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_packs.format import MemoryOverrides, MemoryPack
from namel3ss.runtime.memory_packs.validate import validate_overrides_payload, validate_pack_payload


PACKS_DIR = Path("packs") / "memory"
OVERRIDES_DIR = Path(".namel3ss")
OVERRIDES_FILENAME = "memory_overrides.toml"
OVERRIDES_ALT_FILENAME = "memory_overrides.yaml"


@dataclass(frozen=True)
class PackLoadResult:
    packs: list[MemoryPack]
    overrides: MemoryOverrides | None


def load_memory_packs(*, project_root: str | None, app_path: str | None) -> PackLoadResult:
    root = _resolve_root(project_root=project_root, app_path=app_path)
    if root is None:
        return PackLoadResult(packs=[], overrides=None)
    packs = _load_pack_dirs(root / PACKS_DIR)
    overrides = _load_overrides(root)
    return PackLoadResult(packs=packs, overrides=overrides)


def _load_pack_dirs(packs_root: Path) -> list[MemoryPack]:
    if not packs_root.exists():
        return []
    if not packs_root.is_dir():
        raise Namel3ssError("Memory packs path must be a folder.")
    packs: list[MemoryPack] = []
    for pack_dir in sorted([path for path in packs_root.iterdir() if path.is_dir()], key=lambda p: p.name):
        pack_file = _select_pack_file(pack_dir)
        if pack_file is None:
            raise Namel3ssError("Memory pack is missing pack.toml or pack.yaml.")
        payload = _parse_pack_file(pack_file)
        rules_file = pack_dir / "rules.txt"
        rules = _load_rules_file(rules_file) if rules_file.exists() else None
        pack = validate_pack_payload(payload, rules=rules, source_path=str(pack_file))
        packs.append(pack)
    return packs


def _load_overrides(root: Path) -> MemoryOverrides | None:
    overrides_path = root / OVERRIDES_DIR / OVERRIDES_FILENAME
    alt_path = root / OVERRIDES_DIR / OVERRIDES_ALT_FILENAME
    if overrides_path.exists() and alt_path.exists():
        raise Namel3ssError("Only one memory overrides file is allowed.")
    if overrides_path.exists():
        payload = _parse_toml(overrides_path)
        return validate_overrides_payload(payload, source_path=str(overrides_path))
    if alt_path.exists():
        payload = _parse_yaml(alt_path)
        return validate_overrides_payload(payload, source_path=str(alt_path))
    return None


def _select_pack_file(pack_dir: Path) -> Path | None:
    toml_path = pack_dir / "pack.toml"
    yaml_path = pack_dir / "pack.yaml"
    yml_path = pack_dir / "pack.yml"
    for path in (toml_path, yaml_path, yml_path):
        if path.exists():
            return path
    return None


def _parse_pack_file(path: Path) -> dict:
    if path.suffix == ".toml":
        return _parse_toml(path)
    if path.suffix in {".yaml", ".yml"}:
        return _parse_yaml(path)
    raise Namel3ssError("Memory pack file must be pack.toml or pack.yaml.")


def _parse_toml(path: Path) -> dict:
    try:
        import tomllib  # type: ignore
    except Exception as err:
        raise Namel3ssError("TOML parsing requires tomllib.") from err
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError("Memory pack TOML could not be parsed.") from err
    if not isinstance(data, dict):
        raise Namel3ssError("Memory pack TOML must be a mapping.")
    return data


def _parse_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = _yaml_lines(text)
    data, index = _parse_yaml_block(lines, 0, 0)
    if index != len(lines):
        raise Namel3ssError("Memory pack YAML could not be parsed.")
    if not isinstance(data, dict):
        raise Namel3ssError("Memory pack YAML must be a mapping.")
    return data


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, stripped))
    return lines


def _parse_yaml_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current_indent, current_line = lines[index]
    if current_line.startswith("- "):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_map(lines, index, indent)


def _parse_yaml_map(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict, int]:
    data: dict[str, Any] = {}
    i = index
    while i < len(lines):
        current_indent, current_line = lines[i]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise Namel3ssError("Memory pack YAML indentation is invalid.")
        if current_line.startswith("- "):
            raise Namel3ssError("Memory pack YAML list is not in a field.")
        if ":" not in current_line:
            raise Namel3ssError("Memory pack YAML entry is invalid.")
        key, value = current_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise Namel3ssError("Memory pack YAML entry is invalid.")
        if value:
            data[key] = _parse_yaml_scalar(value)
            i += 1
            continue
        i += 1
        if i >= len(lines) or lines[i][0] <= indent:
            data[key] = {}
            continue
        if lines[i][1].startswith("- "):
            list_value, i = _parse_yaml_list(lines, i, indent + 2)
            data[key] = list_value
        else:
            map_value, i = _parse_yaml_map(lines, i, indent + 2)
            data[key] = map_value
    return data, i


def _parse_yaml_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list, int]:
    items: list[Any] = []
    i = index
    while i < len(lines):
        current_indent, current_line = lines[i]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise Namel3ssError("Memory pack YAML indentation is invalid.")
        if not current_line.startswith("- "):
            raise Namel3ssError("Memory pack YAML list entry is invalid.")
        value = current_line[2:].strip()
        if not value:
            i += 1
            if i >= len(lines) or lines[i][0] <= indent:
                items.append({})
                continue
            if lines[i][1].startswith("- "):
                nested, i = _parse_yaml_list(lines, i, indent + 2)
                items.append(nested)
            else:
                nested, i = _parse_yaml_map(lines, i, indent + 2)
                items.append(nested)
            continue
        if ":" in value:
            key, rest = value.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            item: dict[str, Any] = {}
            if rest:
                item[key] = _parse_yaml_scalar(rest)
            else:
                item[key] = {}
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                nested, i = _parse_yaml_map(lines, i, indent + 2)
                if isinstance(item[key], dict):
                    item[key].update(nested)
                else:
                    item.update(nested)
            items.append(item)
            continue
        items.append(_parse_yaml_scalar(value))
        i += 1
    return items, i


def _parse_yaml_scalar(value: str) -> Any:
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered.isdigit():
        return int(lowered)
    return value


def _load_rules_file(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _resolve_root(*, project_root: str | None, app_path: str | None) -> Path | None:
    if project_root:
        return Path(project_root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None


__all__ = ["PackLoadResult", "load_memory_packs"]
