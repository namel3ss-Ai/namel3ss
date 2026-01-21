from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.registry.catalog import build_catalog
from namel3ss.runtime.registry.resolver import resolve_registry_entries


def get_registry_payload(source: str, body: dict, app_path: str) -> dict:
    _ = source
    app_file = Path(app_path)
    app_root = app_file.parent
    config = load_config(app_path=app_file)
    registry_id, registry_url = _registry_selection(body)
    offline = bool(body.get("offline")) if isinstance(body.get("offline"), bool) else False
    resolution = resolve_registry_entries(
        app_root,
        config,
        registry_id=registry_id,
        registry_url=registry_url,
        phrase="",
        capability=None,
        risk=None,
        offline=offline,
    )
    policy = load_pack_policy(app_root)
    installed_versions = _installed_versions(app_root, config)
    packs = build_catalog(
        resolution.entries,
        policy=policy,
        installed_versions=installed_versions,
        app_root=app_root,
    )
    return {
        "ok": True,
        "count": len(packs),
        "sources": _sources_payload(resolution),
        "selected_sources": list(resolution.selected_ids),
        "packs": [
            {
                "pack_id": pack.pack_id,
                "pack_name": pack.pack_name,
                "installed_version": pack.installed_version,
                "latest_version": pack.latest_version,
                "versions": list(pack.versions),
            }
            for pack in packs
        ],
    }


def _registry_selection(body: dict) -> tuple[str | None, str | None]:
    registry = body.get("registry")
    if not isinstance(registry, str) or not registry:
        return None, None
    if registry.startswith("http://") or registry.startswith("https://"):
        return None, registry
    return registry, None


def _installed_versions(app_root: Path, config) -> dict[str, str]:
    registry = load_pack_registry(app_root, config)
    versions: dict[str, str] = {}
    for pack_id, pack in registry.packs.items():
        if pack.version:
            versions[pack_id] = pack.version
    return versions


def _sources_payload(resolution) -> list[dict[str, object]]:
    sources = []
    for source in resolution.sources:
        sources.append(
            {
                "id": source.id,
                "kind": source.kind,
                "url": source.url if source.kind == "http" else None,
            }
        )
    return sources


__all__ = ["get_registry_payload"]
