from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import zipfile

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.ops import install_pack
from namel3ss.runtime.packs.policy import evaluate_policy, load_pack_policy, policy_denied_message
from namel3ss.runtime.packs.risk import risk_from_summary
from namel3ss.runtime.packs.signature import parse_signature_text, verify_signature
from namel3ss.runtime.packs.source_meta import PackSourceInfo
from namel3ss.runtime.packs.trust_store import load_trusted_keys
from namel3ss.runtime.packs.verification import compute_pack_digest
from namel3ss.runtime.registry.bundle import build_registry_entry_from_bundle
from namel3ss.runtime.registry.entry import RegistryEntry, validate_registry_entry
from namel3ss.runtime.registry.http_client import fetch_registry_bundle
from namel3ss.runtime.registry.layout import REGISTRY_COMPACT, registry_cache_path
from namel3ss.runtime.registry.local_index import (
    append_registry_entry,
    build_compact_index_from_path,
)
from namel3ss.runtime.registry.search import discover_entries, select_best_entry
from namel3ss.runtime.registry.sources import resolve_registry_sources
from namel3ss.runtime.registry.resolver import resolve_registry_entries


def add_bundle_to_registry(app_root: Path, bundle_path: Path) -> RegistryEntry:
    result = build_registry_entry_from_bundle(
        bundle_path,
        app_root=app_root,
        source_kind="local_file",
        source_uri=_source_uri(bundle_path, base_root=app_root),
    )
    stored_path = _store_registry_bundle(app_root, bundle_path, result.entry)
    entry_dict = result.entry.to_dict()
    entry_dict["source"] = {"kind": "local_file", "uri": _source_uri(stored_path, base_root=app_root)}
    entry = RegistryEntry(**entry_dict)
    errors = validate_registry_entry(entry.to_dict())
    if errors:
        raise Namel3ssError(_invalid_entry_message(errors))
    append_registry_entry(app_root, entry)
    return entry


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
    resolution = resolve_registry_entries(
        app_root,
        config,
        registry_id=None,
        registry_url=None,
        phrase=phrase,
        capability=capability,
        risk=risk,
        offline=False,
    )
    return discover_entries(resolution.entries, phrase=phrase, policy=policy, capability_filter=capability, risk_filter=risk)


def install_pack_from_registry(
    app_root: Path,
    config: AppConfig,
    *,
    pack_id: str,
    pack_version: str | None,
    registry_id: str | None,
    registry_url: str | None = None,
    offline: bool = False,
) -> tuple[str, Path]:
    policy = load_pack_policy(app_root)
    if registry_url:
        resolution = resolve_registry_entries(
            app_root,
            config,
            registry_id=None,
            registry_url=registry_url,
            phrase=pack_id,
            capability=None,
            risk=None,
            offline=offline,
        )
        entries = resolution.entries
    else:
        resolution = resolve_registry_entries(
            app_root,
            config,
            phrase=pack_id,
            registry_id=registry_id,
            registry_url=None,
            capability=None,
            risk=None,
            offline=offline,
        )
        entries = resolution.entries
    match = select_best_entry(entries, pack_id=pack_id, pack_version=pack_version, policy=policy)
    if match is None:
        raise Namel3ssError(_missing_pack_message(pack_id))
    if match.blocked:
        raise Namel3ssError(policy_denied_message(pack_id, "add", match.blocked_reasons))
    entry = match.entry
    entry_version = entry.get("pack_version") if isinstance(entry.get("pack_version"), str) else None
    source = entry.get("source")
    if not isinstance(source, dict):
        raise Namel3ssError(_invalid_source_message(pack_id))
    kind = source.get("kind")
    uri = source.get("uri")
    if not isinstance(kind, str) or not isinstance(uri, str):
        raise Namel3ssError(_invalid_source_message(pack_id))
    bundle_path = _resolve_bundle_path(app_root, pack_id, entry_version, entry, kind, uri, offline=offline)
    bundle_info = build_registry_entry_from_bundle(
        bundle_path,
        app_root=app_root,
        source_kind=kind,
        source_uri=uri,
    )
    if bundle_info.entry.pack_digest != entry.get("pack_digest"):
        raise Namel3ssError(_bundle_digest_mismatch_message(pack_id))
    _ensure_entry_match(entry, bundle_info.entry)
    signature_status = _assess_bundle_signature(app_root, bundle_path)
    if signature_status.reason in {"signature_mismatch", "unsupported_signature", "missing_signer_id"}:
        raise Namel3ssError(_bundle_signature_invalid_message(pack_id))
    decision = evaluate_policy(
        policy,
        operation="install",
        verified=signature_status.verified,
        risk=_entry_risk(bundle_info.entry),
        capabilities=bundle_info.entry.capabilities,
        pack_id=bundle_info.entry.pack_id,
        signer_id=signature_status.signer_id,
    )
    if not decision.allowed:
        raise Namel3ssError(policy_denied_message(pack_id, "add", decision.reasons))
    installed_id = install_pack(
        app_root,
        bundle_path,
        source_info=PackSourceInfo(source_type="registry", path=_registry_label(registry_id, registry_url, uri)),
    )
    return installed_id, bundle_path


def _resolve_bundle_path(
    app_root: Path,
    pack_id: str,
    pack_version: str | None,
    entry: dict[str, object],
    kind: str,
    uri: str,
    *,
    offline: bool,
) -> Path:
    if kind == "local_file":
        path = Path(uri)
        if not path.is_absolute():
            path = app_root / path
        if not path.exists():
            raise Namel3ssError(_missing_bundle_message(path))
        return path
    if kind == "registry_url":
        digest = entry.get("pack_digest")
        if not isinstance(digest, str):
            raise Namel3ssError(_invalid_source_message(pack_id))
        cache_root = registry_cache_path(app_root)
        version_label = pack_version or "stable"
        filename = f"{pack_id}-{version_label}-{digest.replace(':', '-')}.n3pack.zip"
        cache_path = cache_root / filename
        if cache_path.exists():
            return cache_path
        if offline:
            raise Namel3ssError(_offline_bundle_message(pack_id))
        return fetch_registry_bundle(uri, digest, cache_path=cache_path)
    raise Namel3ssError(_invalid_source_message(pack_id))


def _store_registry_bundle(app_root: Path, bundle_path: Path, entry: RegistryEntry) -> Path:
    cache_root = registry_cache_path(app_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    filename = _registry_bundle_filename(entry)
    stored_path = cache_root / filename
    if stored_path.exists() and stored_path.stat().st_size > 0:
        return stored_path
    temp_path = stored_path.with_suffix(stored_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    shutil.copyfile(bundle_path, temp_path)
    if temp_path.stat().st_size <= 0:
        raise Namel3ssError(_missing_bundle_message(temp_path))
    temp_path.replace(stored_path)
    return stored_path


def _registry_bundle_filename(entry: RegistryEntry) -> str:
    digest = entry.pack_digest.replace(":", "-")
    return f"{entry.pack_id}-{entry.pack_version}-{digest}.n3pack.zip"

def _missing_pack_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="No matching registry entry is available.",
        fix="Add the bundle to the local registry or check the registry source.",
        example=f"n3 registry add ./dist/{pack_id}.n3pack.zip",
    )


def _missing_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack bundle path was not found.",
        why="Expected the bundle path to exist.",
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


@dataclass(frozen=True)
class BundleSignatureStatus:
    verified: bool
    signer_id: str | None
    reason: str | None


def _assess_bundle_signature(app_root: Path, bundle_path: Path) -> BundleSignatureStatus:
    manifest_text, tools_text, signature_text, signer_id = _read_bundle_signature_payload(bundle_path)
    digest = compute_pack_digest(manifest_text, tools_text)
    if signature_text is None:
        return BundleSignatureStatus(verified=False, signer_id=signer_id, reason="missing_signature")
    payload = parse_signature_text(signature_text)
    if payload is None:
        return BundleSignatureStatus(verified=False, signer_id=signer_id, reason="missing_signature")
    if payload.algorithm not in {"hmac-sha256", "sha256"}:
        return BundleSignatureStatus(verified=False, signer_id=signer_id, reason="unsupported_signature")
    if not signer_id:
        return BundleSignatureStatus(verified=False, signer_id=None, reason="missing_signer_id")
    key = next((item for item in load_trusted_keys(app_root) if item.key_id == signer_id), None)
    if key is None:
        return BundleSignatureStatus(verified=False, signer_id=signer_id, reason="untrusted_signature")
    if not verify_signature(digest, signature_text, key.public_key):
        return BundleSignatureStatus(verified=False, signer_id=signer_id, reason="signature_mismatch")
    return BundleSignatureStatus(verified=True, signer_id=signer_id, reason=None)


def _read_bundle_signature_payload(bundle_path: Path) -> tuple[str, str | None, str | None, str | None]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        manifest_name = _find_name(names, "pack.yaml")
        if not manifest_name:
            raise Namel3ssError(_missing_bundle_message(bundle_path))
        manifest_text = archive.read(manifest_name).decode("utf-8")
        tools_text = _read_optional_text(archive, names, "tools.yaml")
        signature_text = _read_optional_text(archive, names, "signature.txt")
    signer_id = _parse_signer_id(manifest_text)
    return manifest_text, tools_text, signature_text, signer_id


def _parse_signer_id(manifest_text: str) -> str | None:
    for raw in manifest_text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw.lstrip() != raw:
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key.strip() != "signer_id":
            continue
        return _unquote(value.strip())
    return None


def _read_optional_text(archive: zipfile.ZipFile, names: list[str], filename: str) -> str | None:
    match = _find_name(names, filename)
    if not match:
        return None
    return archive.read(match).decode("utf-8")


def _find_name(names: list[str], filename: str) -> str | None:
    matches = [name for name in names if name == filename or name.endswith(f"/{filename}")]
    if not matches:
        return None
    return min(matches, key=len)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def _entry_risk(entry: RegistryEntry) -> str:
    summary = {
        "levels": {
            "filesystem": entry.capabilities.get("filesystem", "none"),
            "network": entry.capabilities.get("network", "none"),
            "env": entry.capabilities.get("env", "none"),
            "subprocess": entry.capabilities.get("subprocess", "none"),
        },
        "secrets": entry.capabilities.get("secrets", []),
    }
    runner_default = entry.runner.get("default") if isinstance(entry.runner, dict) else None
    return risk_from_summary(summary, runner_default)


def _ensure_entry_match(entry: dict[str, object], bundle_entry: RegistryEntry) -> None:
    mismatches: list[str] = []
    if entry.get("pack_id") != bundle_entry.pack_id:
        mismatches.append("pack_id")
    if entry.get("pack_version") != bundle_entry.pack_version:
        mismatches.append("pack_version")
    if entry.get("pack_name") != bundle_entry.pack_name:
        mismatches.append("pack_name")
    if mismatches:
        raise Namel3ssError(_bundle_entry_mismatch_message(bundle_entry.pack_id, mismatches))


def _bundle_entry_mismatch_message(pack_id: str, fields: list[str]) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" does not match the registry entry.',
        why=f"Bundle metadata mismatch: {', '.join(fields)}.",
        fix="Rebuild the bundle or refresh the registry entry.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _bundle_digest_mismatch_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" digest does not match the registry entry.',
        why="The bundle digest differs from the registry index.",
        fix="Rebuild the bundle and update the registry entry.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _bundle_signature_invalid_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" signature is invalid.',
        why="The signature does not match the pack contents.",
        fix="Re-sign the pack and update the registry entry.",
        example="n3 packs sign ./pack --key-id maintainer.key --private-key ./maintainer.key",
    )


def _offline_bundle_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" bundle is not available offline.',
        why="The bundle is not cached locally.",
        fix="Run without --offline or prefetch the bundle.",
        example="n3 pack add pack.name",
    )


def _registry_label(registry_id: str | None, registry_url: str | None, uri: str) -> str:
    if registry_id:
        return f"registry:{registry_id}"
    if registry_url:
        return f"registry:{registry_url}"
    return f"registry:{uri}"


def _source_uri(path: Path, *, base_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(base_root.resolve())
        return relative.as_posix()
    except Exception:
        try:
            relpath = os.path.relpath(path.resolve(), base_root.resolve())
            return Path(relpath).as_posix()
        except Exception:
            return path.name or path.as_posix()


__all__ = ["add_bundle_to_registry", "build_registry_index", "discover_registry", "install_pack_from_registry"]
