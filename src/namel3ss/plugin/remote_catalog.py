from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.module_loader import load_project
from namel3ss.plugin.catalog_entry import ExtensionCatalogEntry
from namel3ss.plugin.remote_registry import (
    list_remote_plugins,
    make_download_url,
    remote_registry_url,
)
from namel3ss.plugin.trust import is_extension_trusted
from namel3ss.versioning.semver import version_sort_key


def resolve_remote_registry_url(
    *,
    project_root: str | Path,
    app_path: str | Path | None,
    registry_override: str | None,
) -> str | None:
    url = remote_registry_url(project_root=project_root, override=registry_override)
    if url is None:
        return None
    explicit_remote_override = isinstance(registry_override, str) and registry_override.strip().lower().startswith(
        ("http://", "https://")
    )
    if app_path is None:
        if explicit_remote_override:
            raise Namel3ssError(
                build_guidance_message(
                    what="Remote registry requires an app path for capability checks.",
                    why="Capability remote_registry must be declared in the app before network registry use.",
                    fix="Run the command with --app <path>.",
                    example="n3 plugin search charts --app app.ai --registry https://registry.example.com",
                )
            )
        return None
    if app_has_capability(app_path, "remote_registry"):
        return url
    if explicit_remote_override:
        raise Namel3ssError(
            build_guidance_message(
                what='Capability "remote_registry" is required.',
                why="Remote plugin registry access is opt-in.",
                fix="Add remote_registry to the app capabilities block.",
                example='capabilities:\n  extension_trust\n  remote_registry',
            )
        )
    return None


def list_remote_registry_extensions(
    *,
    project_root: str | Path,
    base_url: str,
    keyword: str | None = None,
) -> list[ExtensionCatalogEntry]:
    payloads = list_remote_plugins(project_root=project_root, base_url=base_url, keyword=keyword)
    entries = [remote_payload_to_entry(item, base_url=base_url, project_root=project_root) for item in payloads]
    return sorted(entries, key=lambda item: (item.name, version_sort_key(item.version)))


def remote_payload_to_entry(
    payload: dict[str, object],
    *,
    base_url: str,
    project_root: str | Path,
) -> ExtensionCatalogEntry:
    name = str(payload.get("name") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not name or not version:
        raise Namel3ssError("Remote registry entry is missing name or version.")
    digest = str(payload.get("hash") or "").strip()
    if not digest:
        raise Namel3ssError(f"Remote registry entry '{name}@{version}' is missing hash.")
    permissions_raw = payload.get("permissions")
    permissions: tuple[str, ...] = tuple()
    if isinstance(permissions_raw, list):
        permissions = tuple(str(item).strip() for item in permissions_raw if isinstance(item, str) and str(item).strip())
    hooks_raw = payload.get("hooks")
    hooks: tuple[tuple[str, str], ...] = tuple()
    if isinstance(hooks_raw, dict):
        values: list[tuple[str, str]] = []
        for key in sorted(hooks_raw.keys()):
            value = hooks_raw.get(key)
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                values.append((key.strip(), value.strip()))
        hooks = tuple(values)
    trusted = is_extension_trusted(project_root, name=name, version=version, digest=digest)
    raw_download_url = payload.get("download_url")
    download_url: str | None = None
    if isinstance(raw_download_url, str) and raw_download_url.strip():
        if raw_download_url.strip().lower().startswith(("http://", "https://")):
            download_url = raw_download_url.strip()
        else:
            download_url = f"{base_url.rstrip('/')}/{raw_download_url.strip().lstrip('/')}"
    if download_url is None:
        download_url = make_download_url(base_url, name=name, version=version)
    return ExtensionCatalogEntry(
        name=name,
        version=version,
        author=str(payload.get("author") or "unknown"),
        description=str(payload.get("description") or ""),
        permissions=permissions,
        hooks=hooks,
        min_api_version=int(payload.get("min_api_version") or 1),
        signature=str(payload.get("signature")) if payload.get("signature") else None,
        tags=tuple(str(item) for item in payload.get("tags") or [] if isinstance(item, str)),
        rating=float(payload.get("rating")) if isinstance(payload.get("rating"), (int, float)) else None,
        digest=digest,
        source_path=f"remote:{name}@{version}",
        trusted=trusted,
        download_url=download_url,
    )


def app_has_capability(app_path: str | Path, capability: str) -> bool:
    try:
        project = load_project(Path(app_path).resolve())
    except Exception:
        return False
    declared = set()
    for item in list(getattr(project.program, "capabilities", ()) or ()):
        token = normalize_builtin_capability(item if isinstance(item, str) else None)
        if token:
            declared.add(token)
    token = normalize_builtin_capability(capability) or str(capability).strip().lower()
    return token in declared


__all__ = [
    "list_remote_registry_extensions",
    "remote_payload_to_entry",
    "resolve_remote_registry_url",
]
