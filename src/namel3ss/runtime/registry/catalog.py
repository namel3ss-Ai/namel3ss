from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.registry.model import entry_intent_text, normalize_entry
from namel3ss.runtime.registry.pack_version import compare_versions, version_sort_key
from namel3ss.runtime.registry.search import discover_entries
from namel3ss.runtime.registry.trust_evaluator import evaluate_registry_trust
from namel3ss.runtime.packs.policy import PackTrustPolicy


@dataclass(frozen=True)
class CatalogPack:
    pack_id: str
    pack_name: str
    installed_version: str | None
    latest_version: str | None
    versions: list[dict[str, object]]


def build_catalog(
    entries: list[dict[str, object]],
    *,
    policy: PackTrustPolicy,
    installed_versions: dict[str, str],
    app_root,
) -> list[CatalogPack]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for entry in _dedupe_entries(entries):
        pack_id = _str_or_empty(entry.get("pack_id"))
        if not pack_id:
            continue
        grouped.setdefault(pack_id, []).append(entry)
    packs: list[CatalogPack] = []
    for pack_id, pack_entries in grouped.items():
        normalized = [normalize_entry(entry) for entry in pack_entries]
        installed_version = installed_versions.get(pack_id)
        versions = [
            _entry_view(entry, policy=policy, installed_version=installed_version, app_root=app_root)
            for entry in _sort_versions(normalized)
        ]
        pack_name = _pack_name(normalized, pack_id)
        latest_version = versions[0].get("pack_version") if versions else None
        packs.append(
            CatalogPack(
                pack_id=pack_id,
                pack_name=pack_name,
                installed_version=installed_version,
                latest_version=str(latest_version) if isinstance(latest_version, str) else None,
                versions=versions,
            )
        )
    packs.sort(key=lambda item: (item.pack_name.lower(), item.pack_id))
    return packs


def build_search_results(
    entries: list[dict[str, object]],
    *,
    phrase: str,
    policy: PackTrustPolicy,
    installed_versions: dict[str, str],
    app_root,
    capability: str | None,
    risk: str | None,
) -> list[dict[str, object]]:
    matches = discover_entries(entries, phrase=phrase, policy=policy, capability_filter=capability, risk_filter=risk)
    results: list[dict[str, object]] = []
    for match in matches:
        entry = normalize_entry(match.entry)
        pack_id = _str_or_empty(entry.get("pack_id"))
        installed_version = installed_versions.get(pack_id)
        payload = _entry_view(entry, policy=policy, installed_version=installed_version, app_root=app_root)
        payload["match_score"] = match.match_score
        payload["matched_tokens"] = list(match.matched_tokens)
        results.append(payload)
    return results


def build_pack_info(
    entries: list[dict[str, object]],
    *,
    pack_id: str,
    policy: PackTrustPolicy,
    installed_versions: dict[str, str],
    app_root,
) -> CatalogPack | None:
    filtered = [entry for entry in _dedupe_entries(entries) if entry.get("pack_id") == pack_id]
    if not filtered:
        return None
    normalized = [normalize_entry(entry) for entry in filtered]
    installed_version = installed_versions.get(pack_id)
    versions = [
        _entry_view(entry, policy=policy, installed_version=installed_version, app_root=app_root)
        for entry in _sort_versions(normalized)
    ]
    pack_name = _pack_name(normalized, pack_id)
    latest_version = versions[0].get("pack_version") if versions else None
    return CatalogPack(
        pack_id=pack_id,
        pack_name=pack_name,
        installed_version=installed_version,
        latest_version=str(latest_version) if isinstance(latest_version, str) else None,
        versions=versions,
    )


def _entry_view(
    entry: dict[str, object],
    *,
    policy: PackTrustPolicy,
    installed_version: str | None,
    app_root,
) -> dict[str, object]:
    trust = evaluate_registry_trust(entry, policy=policy, app_root=app_root)
    version = _version_status(installed_version, _str_or_empty(entry.get("pack_version")))
    payload = {
        "pack_id": entry.get("pack_id"),
        "pack_name": entry.get("pack_name"),
        "pack_version": entry.get("pack_version"),
        "pack_digest": entry.get("pack_digest"),
        "intent_text": entry_intent_text(entry),
        "intent_phrases": list(entry.get("intent_phrases") or []),
        "tools": list(entry.get("tools") or []),
        "capabilities": entry.get("capabilities", {}),
        "guarantees": entry.get("guarantees"),
        "runner": entry.get("runner", {}),
        "risk": entry.get("risk"),
        "signature": entry.get("signature", {}),
        "signer_id": entry.get("signer_id"),
        "verified_by": list(entry.get("verified_by") or []),
        "source": entry.get("source", {}),
        "trust": {
            "status": trust.status,
            "verified": trust.verified,
            "policy_status": trust.policy_status,
            "policy_reasons": list(trust.policy_reasons),
            "policy_source": trust.policy_source,
        },
        "version": version,
    }
    return payload


def _version_status(installed_version: str | None, candidate_version: str | None) -> dict[str, object]:
    if not installed_version:
        return {"installed": None, "status": "not_installed", "reason": None}
    comparison = compare_versions(installed_version, candidate_version)
    return {
        "installed": installed_version,
        "status": comparison.status,
        "reason": comparison.reason,
    }


def _sort_versions(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        entries,
        key=lambda entry: (version_sort_key(_str_or_empty(entry.get("pack_version"))), _str_or_empty(entry.get("pack_digest"))),
        reverse=True,
    )


def _dedupe_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: dict[str, dict[str, object]] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key:
            seen[key] = entry
    return list(seen.values())


def _entry_key(entry: dict[str, object]) -> str | None:
    pack_id = _str_or_empty(entry.get("pack_id"))
    version = _str_or_empty(entry.get("pack_version"))
    digest = _str_or_empty(entry.get("pack_digest"))
    if not pack_id or not version or not digest:
        return None
    return f"{pack_id}@{version}:{digest}"


def _pack_name(entries: list[dict[str, object]], fallback: str) -> str:
    for entry in entries:
        name = entry.get("pack_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


def _str_or_empty(value: object) -> str:
    return value if isinstance(value, str) else ""


__all__ = ["CatalogPack", "build_catalog", "build_pack_info", "build_search_results"]
