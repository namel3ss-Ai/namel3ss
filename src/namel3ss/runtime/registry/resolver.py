from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.trust_store import load_trusted_keys
from namel3ss.runtime.registry.http_client import fetch_registry_entries
from namel3ss.runtime.registry.layout import REGISTRY_COMPACT
from namel3ss.runtime.registry.local_index import load_registry_entries_from_path
from namel3ss.runtime.registry.sources import RegistrySource, resolve_registry_sources


@dataclass(frozen=True)
class RegistryResolution:
    entries: list[dict[str, object]]
    sources: list[RegistrySource]
    selected_ids: list[str]


def resolve_registry_entries(
    app_root: Path,
    config: AppConfig,
    *,
    registry_id: str | None,
    registry_url: str | None,
    phrase: str,
    capability: str | None,
    risk: str | None,
    offline: bool,
) -> RegistryResolution:
    if registry_url:
        if offline:
            raise Namel3ssError(_offline_registry_message(registry_url))
        entries = fetch_registry_entries(registry_url, phrase=phrase, capability=capability, risk=risk)
        for entry in entries:
            _ensure_registry_source(entry, registry_url)
        _apply_trusted_keys(app_root, entries)
        source = RegistrySource(id="remote", kind="http", url=registry_url)
        return RegistryResolution(entries=entries, sources=[source], selected_ids=[source.id])
    sources, defaults = resolve_registry_sources(app_root, config)
    selected = [registry_id] if registry_id else defaults
    if offline:
        _assert_offline_sources(sources, selected)
    entries: list[dict[str, object]] = []
    for source in sources:
        if source.id not in selected:
            continue
        if source.kind == "local_index":
            entries.extend(_load_local_entries(source))
            continue
        if source.kind == "http" and source.url:
            if offline:
                continue
            remote = fetch_registry_entries(source.url, phrase=phrase, capability=capability, risk=risk)
            for entry in remote:
                _ensure_registry_source(entry, source.url)
            entries.extend(remote)
    _apply_trusted_keys(app_root, entries)
    return RegistryResolution(entries=entries, sources=sources, selected_ids=selected)


def _load_local_entries(source: RegistrySource) -> list[dict[str, object]]:
    if not source.path:
        return []
    compact_path = source.path.parent / REGISTRY_COMPACT
    return load_registry_entries_from_path(source.path, compact_path)


def _ensure_registry_source(entry: dict[str, object], base_url: str) -> None:
    source = entry.get("source")
    if not isinstance(source, dict):
        entry["source"] = {"kind": "registry_url", "uri": base_url}
        return
    if source.get("kind") != "registry_url":
        source["kind"] = "registry_url"
    if not source.get("uri"):
        source["uri"] = base_url


def _apply_trusted_keys(app_root: Path, entries: list[dict[str, object]]) -> None:
    trusted_ids = {key.key_id for key in load_trusted_keys(app_root)}
    for entry in entries:
        verified = entry.get("verified_by")
        if isinstance(verified, list):
            if not trusted_ids:
                entry["verified_by"] = []
            else:
                entry["verified_by"] = [item for item in verified if item in trusted_ids]


def _assert_offline_sources(sources: list[RegistrySource], selected: list[str]) -> None:
    local_available = False
    for source in sources:
        if source.id not in selected:
            continue
        if source.kind == "local_index":
            local_available = True
            continue
        if source.kind == "http":
            raise Namel3ssError(_offline_registry_message(source.id or "remote"))
    if not local_available:
        raise Namel3ssError(_offline_registry_message("remote"))


def _offline_registry_message(registry: str) -> str:
    return build_guidance_message(
        what="Registry access is offline.",
        why=f"Registry {registry} requires network access.",
        fix="Remove --offline or use a local registry.",
        example="n3 registry list --registry local",
    )


__all__ = ["RegistryResolution", "resolve_registry_entries"]
