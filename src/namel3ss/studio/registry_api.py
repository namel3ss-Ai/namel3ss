from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.runtime.registry.ops import add_bundle_to_registry, discover_registry, install_pack_from_registry
from namel3ss.runtime.registry.sources import resolve_registry_sources


def get_registry_status_payload(app_path: str) -> dict:
    try:
        app_file = Path(app_path)
        app_root = app_file.parent
        config = load_config(root=app_root)
        sources, defaults = resolve_registry_sources(app_root, config)
        payload = {
            "ok": True,
            "app_root": str(app_root),
            "sources": [
                {"id": source.id, "kind": source.kind, "path": str(source.path) if source.path else None, "url": source.url}
                for source in sources
            ],
            "default_sources": defaults,
        }
        return payload
    except Namel3ssError as err:
        return {"ok": False, "error": format_error(err, "")}


def apply_registry_add_bundle(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    source = payload.get("path")
    if not isinstance(source, str) or not source:
        return {"ok": False, "error": "path is required"}
    try:
        app_root = Path(app_path).parent
        entry = add_bundle_to_registry(app_root, Path(source))
        return {"ok": True, "pack_id": entry.pack_id, "pack_version": entry.pack_version, "entry": entry.to_dict()}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_discover(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    phrase = payload.get("phrase")
    if not isinstance(phrase, str) or not phrase:
        return {"ok": False, "error": "phrase is required"}
    capability = payload.get("capability")
    risk = payload.get("risk")
    if capability is not None and not isinstance(capability, str):
        return {"ok": False, "error": "capability must be a string"}
    if risk is not None and not isinstance(risk, str):
        return {"ok": False, "error": "risk must be a string"}
    try:
        app_root = Path(app_path).parent
        config = load_config(root=app_root)
        matches = discover_registry(app_root, config, phrase=phrase, capability=capability, risk=risk)
        results = []
        for match in matches:
            entry = match.entry
            results.append(
                {
                    "pack_id": entry.get("pack_id"),
                    "pack_name": entry.get("pack_name"),
                    "pack_version": entry.get("pack_version"),
                    "tools": entry.get("tools"),
                    "capabilities": entry.get("capabilities"),
                    "source": entry.get("source"),
                    "trusted": match.trusted,
                    "risk": match.risk,
                    "blocked_by_policy": match.blocked,
                    "blocked_reasons": match.blocked_reasons,
                    "match_score": match.match_score,
                    "matched_tokens": match.matched_tokens,
                }
            )
        return {"ok": True, "count": len(results), "results": results}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


def apply_pack_install(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Body must be a JSON object"}
    pack_ref = payload.get("pack_ref")
    pack_id = payload.get("pack_id")
    pack_version = payload.get("pack_version")
    if isinstance(pack_ref, str) and "@" in pack_ref:
        pack_id, pack_version = pack_ref.rsplit("@", 1)
    if not isinstance(pack_id, str) or not pack_id:
        return {"ok": False, "error": "pack_id is required"}
    if not isinstance(pack_version, str) or not pack_version:
        return {"ok": False, "error": "pack_version is required"}
    registry_id = payload.get("registry_id")
    if registry_id is not None and not isinstance(registry_id, str):
        return {"ok": False, "error": "registry_id must be a string"}
    try:
        app_root = Path(app_path).parent
        config = load_config(root=app_root)
        installed_id, bundle_path = install_pack_from_registry(
            app_root,
            config,
            pack_id=pack_id,
            pack_version=pack_version,
            registry_id=registry_id,
        )
        return {"ok": True, "pack_id": installed_id, "bundle_path": str(bundle_path)}
    except Namel3ssError as err:
        return {"ok": False, "error": str(err)}


__all__ = [
    "apply_discover",
    "apply_pack_install",
    "apply_registry_add_bundle",
    "get_registry_status_payload",
]
