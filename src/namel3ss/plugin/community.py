from __future__ import annotations

import json
import shutil
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.plugin.catalog_entry import ExtensionCatalogEntry
from namel3ss.plugin.remote_catalog import (
    list_remote_registry_extensions,
    remote_payload_to_entry,
    resolve_remote_registry_url,
)
from namel3ss.plugin.remote_registry import (
    download_remote_plugin,
    remote_plugin_info,
)
from namel3ss.plugin.registry import plugin_registry_root, split_name_and_version
from namel3ss.plugin.trust import (
    TrustedExtensionRecord,
    compute_tree_hash,
    is_extension_trusted,
    revoke_extension,
    trust_extension,
)
from namel3ss.ui.plugins.loader import PLUGIN_MANIFEST_FILES
from namel3ss.ui.plugins.schema import UIPluginSchema, parse_plugin_manifest
from namel3ss.utils.simple_yaml import parse_yaml
from namel3ss.versioning.semver import version_sort_key


def search_registry_extensions(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    keyword: str,
    registry_override: str | None = None,
) -> list[ExtensionCatalogEntry]:
    needle = str(keyword or "").strip().lower()
    remote_url = resolve_remote_registry_url(
        project_root=project_root,
        app_path=app_path,
        registry_override=registry_override,
    )
    if remote_url is not None:
        try:
            return list_remote_registry_extensions(
                project_root=project_root,
                base_url=remote_url,
                keyword=needle,
            )
        except Exception:
            if isinstance(registry_override, str) and registry_override.strip().lower().startswith(("http://", "https://")):
                raise
    entries = list_registry_extensions(
        project_root=project_root,
        app_path=app_path,
        registry_override=registry_override,
    )
    if not needle:
        return entries
    matched: list[ExtensionCatalogEntry] = []
    for entry in entries:
        tags = " ".join(entry.tags)
        haystack = f"{entry.name} {entry.author} {entry.description} {tags}".lower()
        if needle in haystack:
            matched.append(entry)
    return matched


def list_registry_extensions(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    registry_override: str | None = None,
) -> list[ExtensionCatalogEntry]:
    remote_url = resolve_remote_registry_url(
        project_root=project_root,
        app_path=app_path,
        registry_override=registry_override,
    )
    if remote_url is not None:
        try:
            return list_remote_registry_extensions(
                project_root=project_root,
                base_url=remote_url,
            )
        except Exception:
            if isinstance(registry_override, str) and registry_override.strip().lower().startswith(("http://", "https://")):
                raise
    try:
        root = plugin_registry_root(
            project_root=project_root,
            app_path=app_path,
            override=registry_override,
            allow_create=False,
        )
    except Namel3ssError:
        return []
    entries: list[ExtensionCatalogEntry] = []
    for name_dir in sorted([item for item in root.iterdir() if item.is_dir()], key=lambda p: p.name):
        version_dirs = sorted(
            [item for item in name_dir.iterdir() if item.is_dir()],
            key=lambda p: version_sort_key(p.name),
        )
        for version_dir in version_dirs:
            schema = _load_schema(version_dir)
            version = str(schema.version or version_dir.name)
            digest = compute_tree_hash(version_dir)
            trusted = is_extension_trusted(
                project_root,
                name=schema.name,
                version=version,
                digest=digest,
            )
            entries.append(_to_entry(schema, version=version, digest=digest, trusted=trusted, source_path=version_dir))
    return entries


def extension_info(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    name: str,
    version: str | None = None,
    registry_override: str | None = None,
) -> ExtensionCatalogEntry:
    remote_url = resolve_remote_registry_url(
        project_root=project_root,
        app_path=app_path,
        registry_override=registry_override,
    )
    if remote_url is not None:
        try:
            payload = remote_plugin_info(
                project_root=project_root,
                base_url=remote_url,
                name=name,
                version=version,
            )
            return remote_payload_to_entry(
                payload,
                base_url=remote_url,
                project_root=project_root,
            )
        except Exception:
            if isinstance(registry_override, str) and registry_override.strip().lower().startswith(("http://", "https://")):
                raise
    entries = list_registry_extensions(
        project_root=project_root,
        app_path=app_path,
        registry_override=registry_override,
    )
    matches = [entry for entry in entries if entry.name == name]
    if version is not None:
        matches = [entry for entry in matches if entry.version == version]
    if not matches:
        raise Namel3ssError(_missing_registry_entry_message(name, version))
    if version is None:
        return sorted(matches, key=lambda item: version_sort_key(item.version))[-1]
    return matches[0]


def list_installed_extensions(
    *,
    project_root: str | Path,
) -> list[ExtensionCatalogEntry]:
    root = Path(project_root).resolve() / "ui_plugins"
    if not root.exists() or not root.is_dir():
        return []
    entries: list[ExtensionCatalogEntry] = []
    for plugin_dir in sorted([item for item in root.iterdir() if item.is_dir()], key=lambda p: p.name):
        schema = _load_schema(plugin_dir)
        version = str(schema.version or "0.1.0")
        digest = compute_tree_hash(plugin_dir)
        trusted = is_extension_trusted(project_root, name=schema.name, version=version, digest=digest)
        entries.append(_to_entry(schema, version=version, digest=digest, trusted=trusted, source_path=plugin_dir))
    return entries


def install_registry_extension(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    package: str,
    registry_override: str | None = None,
    allow_untrusted: bool = False,
) -> dict[str, object]:
    name, version = split_name_and_version(package)
    entry = extension_info(
        project_root=project_root,
        app_path=app_path,
        name=name,
        version=version,
        registry_override=registry_override,
    )
    source_dir = Path(entry.source_path) if not entry.download_url else None
    destination = Path(project_root).resolve() / "ui_plugins" / entry.name
    if destination.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Extension install target already exists: {destination.as_posix()}",
                why="Install is deterministic and never overwrites an existing extension directory.",
                fix="Remove the directory first or run n3 plugin update.",
                example=f"n3 plugin update {entry.name}",
            )
        )
    if not entry.trusted and not allow_untrusted:
        raise Namel3ssError(_trust_required_message(entry))
    if entry.download_url:
        download_remote_plugin(
            project_root=project_root,
            download_url=entry.download_url,
            destination=destination,
        )
    else:
        if source_dir is None:
            raise Namel3ssError("Registry source path is missing for local extension install.")
        _copy_tree(source_dir, destination)
    installed_hash = compute_tree_hash(destination)
    trusted_record = None
    if not entry.trusted and allow_untrusted:
        trusted_record = trust_extension(
            project_root,
            name=entry.name,
            version=entry.version,
            digest=installed_hash,
            permissions=entry.permissions,
            author=entry.author,
        )
    return {
        "ok": True,
        "name": entry.name,
        "version": entry.version,
        "installed_path": destination.as_posix(),
        "hash": installed_hash,
        "trusted": bool(entry.trusted or trusted_record is not None),
        "permissions": list(entry.permissions),
    }


def update_installed_extension(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    name: str,
    registry_override: str | None = None,
    allow_untrusted: bool = False,
) -> dict[str, object]:
    installed = [item for item in list_installed_extensions(project_root=project_root) if item.name == name]
    if not installed:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Extension '{name}' is not installed.",
                why="Update requires an installed extension.",
                fix="Install the extension first.",
                example=f"n3 plugin install {name}@0.1.0 --yes",
            )
        )
    current = sorted(installed, key=lambda item: version_sort_key(item.version))[-1]
    latest = extension_info(
        project_root=project_root,
        app_path=app_path,
        name=name,
        version=None,
        registry_override=registry_override,
    )
    if version_sort_key(latest.version) <= version_sort_key(current.version):
        return {
            "ok": True,
            "updated": False,
            "name": name,
            "version": current.version,
            "message": "already up to date",
        }
    install_root = Path(project_root).resolve() / "ui_plugins" / name
    if install_root.exists():
        shutil.rmtree(install_root)
    installed_payload = install_registry_extension(
        project_root=project_root,
        app_path=app_path,
        package=f"{name}@{latest.version}",
        registry_override=registry_override,
        allow_untrusted=allow_untrusted,
    )
    return {
        **installed_payload,
        "updated": True,
        "previous_version": current.version,
    }


def trust_extension_package(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    package: str,
    registry_override: str | None = None,
) -> TrustedExtensionRecord:
    name, version = split_name_and_version(package)
    if version is None:
        installed = [entry for entry in list_installed_extensions(project_root=project_root) if entry.name == name]
        if installed:
            target = sorted(installed, key=lambda item: version_sort_key(item.version))[-1]
        else:
            target = extension_info(
                project_root=project_root,
                app_path=app_path,
                name=name,
                version=None,
                registry_override=registry_override,
            )
    else:
        target = extension_info(
            project_root=project_root,
            app_path=app_path,
            name=name,
            version=version,
            registry_override=registry_override,
        )
    return trust_extension(
        project_root,
        name=target.name,
        version=target.version,
        digest=target.digest,
        permissions=target.permissions,
        author=target.author,
    )


def revoke_extension_trust(
    *,
    project_root: str | Path,
    package: str,
) -> int:
    name, version = split_name_and_version(package)
    return revoke_extension(project_root, name=name, version=version)


def _to_entry(
    schema: UIPluginSchema,
    *,
    version: str,
    digest: str,
    trusted: bool,
    source_path: Path,
    download_url: str | None = None,
) -> ExtensionCatalogEntry:
    return ExtensionCatalogEntry(
        name=schema.name,
        version=version,
        author=str(schema.author or "unknown"),
        description=str(schema.description or ""),
        permissions=tuple(schema.permissions),
        hooks=tuple(schema.hooks),
        min_api_version=int(schema.min_api_version),
        signature=schema.signature,
        tags=tuple(schema.tags),
        rating=schema.rating,
        digest=digest,
        source_path=source_path.as_posix(),
        trusted=trusted,
        download_url=download_url,
    )


def _load_schema(plugin_root: Path) -> UIPluginSchema:
    manifest_path = _find_manifest(plugin_root)
    payload = _read_manifest_payload(manifest_path)
    return parse_plugin_manifest(payload, source_path=manifest_path, plugin_root=plugin_root)


def _find_manifest(plugin_root: Path) -> Path:
    for filename in PLUGIN_MANIFEST_FILES:
        path = plugin_root / filename
        if path.exists() and path.is_file():
            return path.resolve()
    expected = ", ".join(PLUGIN_MANIFEST_FILES)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Extension manifest not found in {plugin_root.as_posix()}",
            why=f"Expected one of: {expected}.",
            fix="Add a plugin manifest to the extension package.",
            example="plugin.yaml",
        )
    )


def _read_manifest_payload(path: Path) -> object:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                f"Invalid JSON in extension manifest '{path.as_posix()}': {err.msg}",
                line=err.lineno,
                column=err.colno,
            ) from err
    try:
        return parse_yaml(raw)
    except Exception as err:
        raise Namel3ssError(f"Invalid YAML in extension manifest '{path.as_posix()}': {err}") from err


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


def _missing_registry_entry_message(name: str, version: str | None) -> str:
    suffix = f"@{version}" if isinstance(version, str) else ""
    return build_guidance_message(
        what=f"Extension '{name}{suffix}' was not found in the registry.",
        why="No published entry matched the requested package.",
        fix="Run n3 plugin search to inspect available packages.",
        example=f"n3 plugin search {name}",
    )


def _trust_required_message(entry: ExtensionCatalogEntry) -> str:
    perms = ", ".join(entry.permissions) if entry.permissions else "none"
    hooks = ", ".join(kind for kind, _ in entry.hooks) if entry.hooks else "none"
    return build_guidance_message(
        what=f"Extension '{entry.name}@{entry.version}' is not trusted.",
        why=f"Permissions: {perms}. Hooks: {hooks}.",
        fix="Trust the extension first or install with explicit consent.",
        example=f"n3 plugin trust {entry.name}@{entry.version} --yes",
    )


__all__ = [
    "ExtensionCatalogEntry",
    "extension_info",
    "install_registry_extension",
    "list_installed_extensions",
    "list_registry_extensions",
    "revoke_extension_trust",
    "search_registry_extensions",
    "trust_extension_package",
    "update_installed_extension",
]
