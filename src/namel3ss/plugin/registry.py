from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ui.plugins.loader import PLUGIN_MANIFEST_FILES
from namel3ss.ui.plugins.schema import parse_plugin_manifest
from namel3ss.utils.simple_yaml import parse_yaml
from namel3ss.versioning.semver import version_sort_key


@dataclass(frozen=True)
class PluginRegistryEntry:
    name: str
    version: str
    hash: str
    source_path: str

    def to_payload(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "hash": self.hash,
            "source_path": self.source_path,
        }


def plugin_registry_root(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    override: str | None = None,
    allow_create: bool = True,
) -> Path:
    if override:
        root = Path(override).expanduser().resolve()
    else:
        root = Path(project_root).resolve() / ".namel3ss" / "plugin_registry"
    if allow_create:
        root.mkdir(parents=True, exist_ok=True)
        return root
    if root.exists():
        return root
    raise Namel3ssError(
        build_guidance_message(
            what=f"Plugin registry path does not exist: {root.as_posix()}",
            why="No plugins were published yet for this registry.",
            fix="Publish a plugin first or provide --registry with an existing path.",
            example="n3 publish plugin ./plugins/charts",
        )
    )


def publish_plugin(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    plugin_path: str | Path,
    registry_override: str | None = None,
) -> dict[str, object]:
    plugin_root = Path(plugin_path).expanduser().resolve()
    _ensure_plugin_directory(plugin_root)
    manifest_path = _find_manifest_path(plugin_root)
    payload = _read_manifest_payload(manifest_path)
    schema = parse_plugin_manifest(payload, source_path=manifest_path, plugin_root=plugin_root)
    version = str(schema.version or "0.1.0").strip()
    if not version:
        version = "0.1.0"
    registry_root = plugin_registry_root(
        project_root=project_root,
        app_path=app_path,
        override=registry_override,
        allow_create=True,
    )
    target = registry_root / schema.name / version
    if target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Plugin '{schema.name}@{version}' already exists in the registry.",
                why="Publishing is immutable for deterministic installs.",
                fix="Bump the plugin version and publish again.",
                example=f"n3 publish plugin {plugin_root.as_posix()}",
            )
        )
    _copy_tree(plugin_root, target)
    digest = _tree_hash(target)
    return {
        "ok": True,
        "name": schema.name,
        "version": version,
        "hash": digest,
        "registry_path": target.as_posix(),
    }


def install_plugin(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    name: str,
    version: str | None = None,
    registry_override: str | None = None,
) -> dict[str, object]:
    registry_root = plugin_registry_root(
        project_root=project_root,
        app_path=app_path,
        override=registry_override,
        allow_create=False,
    )
    name_dir = registry_root / name
    if not name_dir.exists() or not name_dir.is_dir():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Plugin '{name}' was not found in the registry.",
                why="No published versions matched this name.",
                fix="Run n3 list plugins to inspect available names.",
                example="n3 list plugins",
            )
        )
    selected_version = version or _latest_version(name_dir)
    source_dir = name_dir / selected_version
    if not source_dir.exists() or not source_dir.is_dir():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Plugin '{name}@{selected_version}' was not found in the registry.",
                why="The requested version does not exist.",
                fix="Use n3 list plugins to find an available version.",
                example=f"n3 install plugin {name}@{_latest_version(name_dir)}",
            )
        )
    destination = Path(project_root).resolve() / "ui_plugins" / name
    if destination.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Plugin install target already exists: {destination.as_posix()}",
                why="Install does not overwrite existing plugin files.",
                fix="Remove the existing directory before installing again.",
                example=f"rm -rf {destination.as_posix()} && n3 install plugin {name}@{selected_version}",
            )
        )
    _copy_tree(source_dir, destination)
    digest = _tree_hash(destination)
    return {
        "ok": True,
        "name": name,
        "version": selected_version,
        "hash": digest,
        "installed_path": destination.as_posix(),
    }


def list_plugins(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    registry_override: str | None = None,
) -> list[PluginRegistryEntry]:
    try:
        registry_root = plugin_registry_root(
            project_root=project_root,
            app_path=app_path,
            override=registry_override,
            allow_create=False,
        )
    except Namel3ssError:
        return []
    entries: list[PluginRegistryEntry] = []
    for name_dir in sorted([item for item in registry_root.iterdir() if item.is_dir()], key=lambda p: p.name):
        versions = sorted([item for item in name_dir.iterdir() if item.is_dir()], key=lambda p: version_sort_key(p.name))
        for version_dir in versions:
            entries.append(
                PluginRegistryEntry(
                    name=name_dir.name,
                    version=version_dir.name,
                    hash=_tree_hash(version_dir),
                    source_path=version_dir.as_posix(),
                )
            )
    return entries


def split_name_and_version(value: str) -> tuple[str, str | None]:
    text = str(value or "").strip()
    if not text:
        raise Namel3ssError(
            build_guidance_message(
                what="Plugin name is required.",
                why="Install command did not receive a plugin name.",
                fix="Pass <name> or <name>@<version>.",
                example="n3 install plugin charts@0.1.0",
            )
        )
    if "@" not in text:
        return text, None
    name, version = text.split("@", 1)
    if not name.strip():
        raise Namel3ssError("Plugin name before '@' cannot be empty.")
    if not version.strip():
        raise Namel3ssError("Plugin version after '@' cannot be empty.")
    return name.strip(), version.strip()


def _latest_version(name_dir: Path) -> str:
    versions = [item.name for item in name_dir.iterdir() if item.is_dir()]
    if not versions:
        raise Namel3ssError(
            build_guidance_message(
                what=f"No versions were found for plugin '{name_dir.name}'.",
                why="The registry entry is empty.",
                fix="Publish a plugin version first.",
                example=f"n3 publish plugin ./plugins/{name_dir.name}",
            )
        )
    return sorted(versions, key=version_sort_key)[-1]


def _ensure_plugin_directory(path: Path) -> None:
    if path.exists() and path.is_dir():
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"Plugin path does not exist: {path.as_posix()}",
            why="Publish expects a plugin directory.",
            fix="Pass the path to a generated plugin package directory.",
            example="n3 publish plugin ./charts",
        )
    )


def _find_manifest_path(plugin_root: Path) -> Path:
    for filename in PLUGIN_MANIFEST_FILES:
        candidate = plugin_root / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    expected = ", ".join(PLUGIN_MANIFEST_FILES)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Plugin manifest not found in {plugin_root.as_posix()}",
            why=f"Expected one of: {expected}.",
            fix="Add plugin.json (or plugin.yaml) to the plugin directory.",
            example="n3 create plugin charts",
        )
    )


def _read_manifest_payload(manifest_path: Path) -> object:
    raw = manifest_path.read_text(encoding="utf-8")
    suffix = manifest_path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                f"Invalid JSON in plugin manifest '{manifest_path.as_posix()}': {err.msg}",
                line=err.lineno,
                column=err.colno,
            ) from err
    try:
        return parse_yaml(raw)
    except Exception as err:
        raise Namel3ssError(f"Invalid YAML in plugin manifest '{manifest_path.as_posix()}': {err}") from err


def _copy_tree(source_root: Path, target_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=False)
    for source_path in sorted(source_root.rglob("*"), key=lambda p: p.as_posix()):
        rel = source_path.relative_to(source_root)
        target_path = target_root / rel
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        if source_path.is_file():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted([item for item in root.rglob("*") if item.is_file()], key=lambda p: p.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


__all__ = [
    "PluginRegistryEntry",
    "install_plugin",
    "list_plugins",
    "plugin_registry_root",
    "publish_plugin",
    "split_name_and_version",
]
