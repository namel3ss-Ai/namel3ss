from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.simple_yaml import parse_yaml

from .schema import UIPluginSchema, parse_plugin_manifest

PLUGIN_MANIFEST_FILES = (
    "plugin.yaml",
    "plugin.yml",
    "plugin.json",
    "manifest.yaml",
    "manifest.yml",
    "manifest.json",
)


def resolve_plugin_directories(*, project_root: str | Path | None, app_path: str | Path | None) -> tuple[Path, ...]:
    dirs: list[Path] = []
    env_dirs = _read_env_directories()
    dirs.extend(env_dirs)

    root = _resolve_root(project_root, app_path)
    if root is not None:
        dirs.append((root / ".namel3ss" / "ui_plugins").resolve())
        dirs.append((root / "ui_plugins").resolve())
        dirs.append((root / "plugins").resolve())

    unique: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        key = directory.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique.append(directory)
    return tuple(unique)


def load_plugin_schema(
    plugin_name: str,
    *,
    directories: tuple[Path, ...],
) -> UIPluginSchema:
    if not plugin_name or not plugin_name.strip():
        raise Namel3ssError("Plug-in name must be a non-empty string.")
    name = plugin_name.strip()

    plugin_root = _find_plugin_root(name, directories)
    manifest_path = _find_manifest(plugin_root)
    payload = _read_manifest_payload(manifest_path)
    schema = parse_plugin_manifest(payload, source_path=manifest_path, plugin_root=plugin_root)
    if schema.name != name:
        raise Namel3ssError(
            f"UI plug-in manifest name mismatch: requested '{name}' but manifest declares '{schema.name}'."
        )
    return schema


def _read_env_directories() -> list[Path]:
    raw = os.getenv("N3_UI_PLUGIN_DIRS", "")
    if not raw.strip():
        return []
    values: list[Path] = []
    for segment in raw.split(os.pathsep):
        text = segment.strip()
        if not text:
            continue
        values.append(Path(text).expanduser().resolve())
    return values


def _resolve_root(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    if project_root is not None:
        return Path(project_root).expanduser().resolve()
    if app_path is not None:
        return Path(app_path).expanduser().resolve().parent
    return None


def _find_plugin_root(name: str, directories: tuple[Path, ...]) -> Path:
    checked: list[str] = []
    for directory in directories:
        candidate = directory / name
        checked.append(candidate.as_posix())
        if candidate.is_dir():
            return candidate.resolve()
    search_paths = ", ".join(checked) if checked else "<none>"
    raise Namel3ssError(
        f"Unknown UI plug-in '{name}'. Checked: {search_paths}. Set N3_UI_PLUGIN_DIRS or add the plug-in directory."
    )


def _find_manifest(plugin_root: Path) -> Path:
    for filename in PLUGIN_MANIFEST_FILES:
        path = plugin_root / filename
        if path.exists() and path.is_file():
            return path.resolve()
    expected = ", ".join(PLUGIN_MANIFEST_FILES)
    raise Namel3ssError(
        f"UI plug-in '{plugin_root.name}' is missing a manifest file. Expected one of: {expected}."
    )


def _read_manifest_payload(manifest_path: Path) -> object:
    raw = manifest_path.read_text(encoding="utf-8")
    suffix = manifest_path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                f"UI plug-in manifest '{manifest_path.as_posix()}' is invalid JSON: {err.msg}",
                line=err.lineno,
                column=err.colno,
            ) from err
    try:
        return parse_yaml(raw)
    except Exception as err:
        raise Namel3ssError(f"UI plug-in manifest '{manifest_path.as_posix()}' is invalid YAML: {err}") from err


__all__ = [
    "PLUGIN_MANIFEST_FILES",
    "load_plugin_schema",
    "resolve_plugin_directories",
]
