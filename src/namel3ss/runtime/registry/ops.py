from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import install_pack
from namel3ss.runtime.packs.trust_store import load_trusted_keys
from namel3ss.runtime.packs.policy import load_pack_policy, policy_denied_message
from namel3ss.runtime.registry.bundle import build_registry_entry_from_bundle
from namel3ss.runtime.registry.entry import RegistryEntry, validate_registry_entry
from namel3ss.runtime.registry.http_client import fetch_registry_bundle, fetch_registry_entries
from namel3ss.runtime.registry.layout import REGISTRY_COMPACT, registry_cache_path
from namel3ss.runtime.registry.local_index import (
    append_registry_entry,
    build_compact_index_from_path,
    load_registry_entries_from_path,
)
from namel3ss.runtime.registry.search import discover_entries, select_best_entry
from namel3ss.runtime.registry.sources import RegistrySource, resolve_registry_sources


def add_bundle_to_registry(app_root: Path, bundle_path: Path) -> RegistryEntry:
    result = build_registry_entry_from_bundle(
        bundle_path,
        app_root=app_root,
        source_kind="local_file",
        source_uri=str(bundle_path.resolve()),
    )
    entry_dict = result.entry.to_dict()
    errors = validate_registry_entry(entry_dict)
    if errors:
        raise Namel3ssError(_invalid_entry_message(errors))
    append_registry_entry(app_root, result.entry)
    return result.entry


def build_registry_index(app_root: Path, config: AppConfig) -> Path:
    sources, _ = resolve_registry_sources(app_root, config)
    local = next((source for source in sources if source.kind == "local_index"), None)
    if not local or not local.path:
        raise Namel3ssError(_missing_local_source_message())
    compact_path = local.path.parent / REGISTRY_COMPACT
    return build_compact_index_from_path(local.path, compact_path)


def discover_registry(
    app_root: Path,
    config: AppConfig,
    *,
    phrase: str,
    capability: str | None,
    risk: str | None,
) -> list:
    policy = load_pack_policy(app_root)
    entries = _collect_entries(app_root, config, phrase=phrase, capability=capability, risk=risk)
    return discover_entries(entries, phrase=phrase, policy=policy, capability_filter=capability, risk_filter=risk)


def install_pack_from_registry(
    app_root: Path,
    config: AppConfig,
    *,
    pack_id: str,
    pack_version: str,
    registry_id: str | None,
) -> tuple[str, Path]:
    policy = load_pack_policy(app_root)
    entries = _collect_entries(app_root, config, phrase=pack_id, registry_id=registry_id, capability=None, risk=None)
    match = select_best_entry(entries, pack_id=pack_id, pack_version=pack_version, policy=policy)
    if match is None:
        raise Namel3ssError(_missing_pack_message(pack_id, pack_version))
    if match.blocked:
        raise Namel3ssError(policy_denied_message(pack_id, "add", match.blocked_reasons))
    entry = match.entry
    source = entry.get("source")
    if not isinstance(source, dict):
        raise Namel3ssError(_invalid_source_message(pack_id))
    kind = source.get("kind")
    uri = source.get("uri")
    if not isinstance(kind, str) or not isinstance(uri, str):
        raise Namel3ssError(_invalid_source_message(pack_id))
    bundle_path = _resolve_bundle_path(app_root, pack_id, pack_version, entry, kind, uri)
    installed_id = install_pack(app_root, bundle_path)
    return installed_id, bundle_path


def _collect_entries(
    app_root: Path,
    config: AppConfig,
    *,
    phrase: str,
    registry_id: str | None = None,
    capability: str | None,
    risk: str | None,
) -> list[dict[str, object]]:
    sources, defaults = resolve_registry_sources(app_root, config)
    selected = [registry_id] if registry_id else defaults
    entries: list[dict[str, object]] = []
    for source in sources:
        if source.id not in selected:
            continue
        if source.kind == "local_index":
            entries.extend(_load_local_entries(source))
            continue
        if source.kind == "http" and source.url:
            remote = fetch_registry_entries(source.url, phrase=phrase, capability=capability, risk=risk)
            for entry in remote:
                _ensure_registry_source(entry, source.url)
            entries.extend(remote)
    _apply_trusted_keys(app_root, entries)
    return entries


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


def _resolve_bundle_path(
    app_root: Path,
    pack_id: str,
    pack_version: str,
    entry: dict[str, object],
    kind: str,
    uri: str,
) -> Path:
    if kind == "local_file":
        path = Path(uri)
        if not path.exists():
            raise Namel3ssError(_missing_bundle_message(path))
        return path
    if kind == "registry_url":
        digest = entry.get("pack_digest")
        if not isinstance(digest, str):
            raise Namel3ssError(_invalid_source_message(pack_id))
        cache_root = registry_cache_path(app_root)
        filename = f"{pack_id}-{pack_version}-{digest.replace(':', '-')}.n3pack.zip"
        cache_path = cache_root / filename
        if cache_path.exists():
            return cache_path
        return fetch_registry_bundle(uri, digest, cache_path=cache_path)
    raise Namel3ssError(_invalid_source_message(pack_id))


def _missing_pack_message(pack_id: str, pack_version: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}@{pack_version}" was not found.',
        why="No matching registry entry is available.",
        fix="Add the bundle to the local registry or check the registry source.",
        example=f"n3 registry add ./dist/{pack_id}-{pack_version}.n3pack.zip",
    )


def _missing_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack bundle path was not found.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Rebuild or re-download the pack bundle.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _invalid_source_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" registry source is invalid.',
        why="Registry entries must include a source kind and uri.",
        fix="Rebuild the registry entry.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _invalid_entry_message(errors: list[str]) -> str:
    return build_guidance_message(
        what="Registry entry is invalid.",
        why="; ".join(errors),
        fix="Rebuild the registry entry.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _missing_local_source_message() -> str:
    return build_guidance_message(
        what="Local registry source is missing.",
        why="The registry config does not include a local_index source.",
        fix="Add a local registry source to namel3ss.toml.",
        example='[registries]\\nsources = [{ id="local", kind="local_index", path=".namel3ss/registry/index.jsonl" }]',
    )


__all__ = ["add_bundle_to_registry", "build_registry_index", "discover_registry", "install_pack_from_registry"]
