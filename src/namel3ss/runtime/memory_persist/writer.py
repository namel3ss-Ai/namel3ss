from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_persist.format import (
    MEMORY_STORE_VERSION,
    encode_budget_config,
    encode_cache_value,
    encode_handoff_packet,
    encode_memory_item,
    encode_phase_info,
    encode_proposal,
    encode_snapshot_item,
    encode_trust_rules,
)
from namel3ss.runtime.memory_persist.paths import memory_dir, snapshot_paths
from namel3ss.runtime.memory_persist.verify import verify_snapshot_payload
from namel3ss.runtime.memory_rules.model import RULE_STATUS_ACTIVE
from namel3ss.runtime.memory_rules.store import is_rule_item
from namel3ss.runtime.memory_timeline.snapshot import PhaseSnapshot, SnapshotItem
from namel3ss.runtime.memory_trust.model import TrustRules
from namel3ss.runtime.memory.spaces import resolve_space_context


def write_snapshot(
    manager,
    *,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None = None,
) -> Path | None:
    snapshot_path, checksum_path = snapshot_paths(project_root=project_root, app_path=app_path, for_write=True)
    if snapshot_path is None or checksum_path is None:
        return None
    payload = build_snapshot_payload(
        manager,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    verify_snapshot_payload(payload)
    data = serialize_snapshot(payload)
    target_dir = memory_dir(project_root=project_root, app_path=app_path, for_write=True)
    if target_dir is None:
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(snapshot_path, data)
    checksum = hashlib.sha256(data.encode("utf-8")).hexdigest()
    _atomic_write(checksum_path, f"{checksum}\n")
    return snapshot_path


def build_snapshot_payload(
    manager,
    *,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None = None,
) -> dict:
    project_id = _project_id(project_root=project_root, app_path=app_path)
    budgets = [encode_budget_config(cfg) for cfg in list(getattr(manager, "_budgets", []))]
    trust_rules = getattr(manager, "_trust_rules", None)
    if isinstance(trust_rules, TrustRules):
        trust_payload = encode_trust_rules(trust_rules)
    else:
        trust_payload = None
    return {
        "version": MEMORY_STORE_VERSION,
        "project_id": project_id,
        "clock": {"tick": int(getattr(manager, "_clock").current())},
        "ids": {"counters": _encode_id_counters(getattr(manager, "_ids"))},
        "phases": _encode_phase_registry(getattr(manager, "_phases")),
        "ledger": _encode_phase_ledger(getattr(manager, "_ledger")),
        "items": _encode_items(manager, secret_values=secret_values),
        "agreements": _encode_agreements(manager, secret_values=secret_values),
        "handoffs": _encode_handoffs(manager),
        "budgets": budgets,
        "cache": _encode_cache(manager, secret_values=secret_values),
        "cache_versions": _encode_cache_versions(manager),
        "rules": _encode_rules(manager),
        "trust": trust_payload,
    }


def serialize_snapshot(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _project_id(*, project_root: str | None, app_path: str | None) -> str:
    space_ctx = resolve_space_context(
        None,
        project_root=project_root,
        app_path=app_path,
    )
    return space_ctx.project_id


def _encode_id_counters(ids) -> list[dict]:
    counters = []
    raw = getattr(ids, "_counters", {})
    for (store_key, kind), value in raw.items():
        counters.append({"store_key": store_key, "kind": getattr(kind, "value", str(kind)), "counter": int(value)})
    counters.sort(key=lambda entry: (entry["store_key"], entry["kind"]))
    return counters


def _encode_phase_registry(registry) -> dict:
    counters = {key: int(value) for key, value in getattr(registry, "_counters", {}).items()}
    current = {key: encode_phase_info(info) for key, info in getattr(registry, "_current", {}).items()}
    history = {
        key: [encode_phase_info(info) for info in infos]
        for key, infos in getattr(registry, "_history", {}).items()
    }
    last_token = {key: str(value) for key, value in getattr(registry, "_last_token", {}).items()}
    return {
        "counters": _sorted_map(counters),
        "current": _sorted_map(current),
        "history": _sorted_map(history),
        "last_token": _sorted_map(last_token),
    }


def _encode_phase_ledger(ledger) -> dict:
    snapshots = {}
    for store_key, by_phase in getattr(ledger, "_snapshots", {}).items():
        snapshots[store_key] = {}
        for phase_id, snapshot in by_phase.items():
            snapshots[store_key][phase_id] = _encode_phase_snapshot(snapshot)
    order = {key: list(values) for key, values in getattr(ledger, "_order", {}).items()}
    return {"snapshots": _sorted_map(snapshots), "order": _sorted_map(order)}


def _encode_phase_snapshot(snapshot: PhaseSnapshot) -> dict:
    items = {key: encode_snapshot_item(value) for key, value in snapshot.items.items()}
    dedupe_map = dict(snapshot.dedupe_map)
    return {
        "phase_id": snapshot.phase_id,
        "phase_index": int(snapshot.phase_index),
        "items": _sorted_map(items),
        "dedupe_map": _sorted_map(dedupe_map),
    }


def _encode_items(manager, *, secret_values: list[str] | None) -> dict:
    stores = []
    store_keys = _collect_store_keys(manager)
    for store_key in sorted(store_keys):
        space, owner, lane = _split_store_key(store_key)
        phases = _encode_store_phases(manager, store_key, secret_values=secret_values)
        stores.append(
            {
                "store_key": store_key,
                "space": space,
                "owner": owner,
                "lane": lane,
                "phases": phases,
            }
        )
    return {"stores": stores}


def _encode_store_phases(manager, store_key: str, *, secret_values: list[str] | None) -> list[dict]:
    phase_map: dict[str, dict] = {}
    short_term = getattr(manager, "short_term", None)
    if short_term is not None:
        messages_by_phase = getattr(short_term, "_messages", {}).get(store_key, {})
        for phase_id, items in messages_by_phase.items():
            entry = _phase_entry(phase_map, phase_id)
            entry["short_term"]["messages"] = [
                encode_memory_item(item, secret_values=secret_values) for item in list(items)
            ]
        summaries_by_phase = getattr(short_term, "_summaries", {}).get(store_key, {})
        for phase_id, summary in summaries_by_phase.items():
            entry = _phase_entry(phase_map, phase_id)
            entry["short_term"]["summaries"] = [encode_memory_item(summary, secret_values=secret_values)]
    semantic = getattr(manager, "semantic", None)
    if semantic is not None:
        for item in getattr(semantic, "_snippets", {}).get(store_key, []):
            phase_id = _phase_id_for_item(item)
            entry = _phase_entry(phase_map, phase_id)
            entry["semantic"].append(encode_memory_item(item, secret_values=secret_values))
    profile = getattr(manager, "profile", None)
    if profile is not None:
        facts = getattr(profile, "_facts", {}).get(store_key, {})
        for key in sorted(facts.keys()):
            item = facts[key]
            phase_id = _phase_id_for_item(item)
            entry = _phase_entry(phase_map, phase_id)
            entry["profile"].append(encode_memory_item(item, secret_values=secret_values))
    phases = []
    for phase_id in sorted(phase_map.keys()):
        phases.append(phase_map[phase_id])
    return phases


def _encode_agreements(manager, *, secret_values: list[str] | None) -> dict:
    store = getattr(manager, "agreements", None)
    if store is None:
        return {"counter": 0, "tick": 0, "pending": [], "history": {}}
    pending = [
        encode_proposal(proposal, secret_values=secret_values)
        for proposal in getattr(store, "_pending_by_id", {}).values()
    ]
    pending.sort(key=lambda entry: (entry.get("proposed_at", 0), entry.get("proposal_id", "")))
    history = {}
    for team_id, records in getattr(store, "_history", {}).items():
        history[team_id] = [
            {
                "proposal_id": record.proposal_id,
                "status": record.status,
                "phase_id": record.phase_id,
                "decided_at": int(record.decided_at),
            }
            for record in records
        ]
    return {
        "counter": int(getattr(store, "_counter", 0)),
        "tick": int(getattr(store, "_tick", 0)),
        "pending": pending,
        "history": _sorted_map(history),
    }


def _encode_handoffs(manager) -> dict:
    store = getattr(manager, "handoffs", None)
    if store is None:
        return {"counter": 0, "tick": 0, "packets": []}
    packets = [encode_handoff_packet(packet) for packet in getattr(store, "_by_id", {}).values()]
    packets.sort(key=lambda entry: (entry.get("created_at", 0), entry.get("packet_id", "")))
    return {
        "counter": int(getattr(store, "_counter", 0)),
        "tick": int(getattr(store, "_tick", 0)),
        "packets": packets,
    }


def _encode_cache(manager, *, secret_values: list[str] | None) -> dict:
    cache = getattr(manager, "_cache", None)
    if cache is None:
        return {"max_entries": 0, "counter": 0, "entries": []}
    entries = []
    raw_entries = getattr(cache, "_entries", {})
    for key, entry in raw_entries.items():
        version = entry.version
        if isinstance(version, tuple):
            version = list(version)
        entries.append(
            {
                "key": key,
                "inserted_at": int(entry.inserted_at),
                "version": version,
                "value": encode_cache_value(entry.value, secret_values=secret_values),
            }
        )
    entries.sort(key=lambda entry: (entry.get("inserted_at", 0), entry.get("key", "")))
    return {
        "max_entries": int(getattr(cache, "_max_entries", 0)),
        "counter": int(getattr(cache, "_counter", 0)),
        "entries": entries,
    }


def _encode_cache_versions(manager) -> list[dict]:
    versions = []
    raw = getattr(manager, "_cache_versions", {})
    for (store_key, kind), value in raw.items():
        versions.append({"store_key": store_key, "kind": kind, "version": int(value)})
    versions.sort(key=lambda entry: (entry["store_key"], entry["kind"]))
    return versions


def _encode_rules(manager) -> dict:
    semantic = getattr(manager, "semantic", None)
    active_ids: list[str] = []
    if semantic is not None:
        for item in semantic.all_items():
            if not is_rule_item(item):
                continue
            status = item.meta.get("rule_status") if isinstance(item, MemoryItem) else None
            if status == RULE_STATUS_ACTIVE or status is None:
                active_ids.append(item.id)
    pending_ids = []
    agreements = getattr(manager, "agreements", None)
    if agreements is not None:
        for proposal in getattr(agreements, "_pending_by_id", {}).values():
            if not is_rule_item(proposal.memory_item):
                continue
            pending_ids.append(proposal.memory_item.id)
    return {
        "active_rule_ids": sorted(active_ids),
        "pending_rule_ids": sorted(pending_ids),
    }


def _collect_store_keys(manager) -> set[str]:
    keys = set()
    short_term = getattr(manager, "short_term", None)
    if short_term is not None:
        keys.update(getattr(short_term, "_messages", {}).keys())
        keys.update(getattr(short_term, "_summaries", {}).keys())
    semantic = getattr(manager, "semantic", None)
    if semantic is not None:
        keys.update(getattr(semantic, "_snippets", {}).keys())
    profile = getattr(manager, "profile", None)
    if profile is not None:
        keys.update(getattr(profile, "_facts", {}).keys())
    return keys


def _split_store_key(store_key: str) -> tuple[str, str, str]:
    parts = store_key.split(":")
    if len(parts) < 3:
        return "unknown", "unknown", "unknown"
    space = parts[0]
    lane = parts[-1]
    owner = ":".join(parts[1:-1])
    return space, owner, lane


def _phase_entry(phase_map: dict[str, dict], phase_id: str) -> dict:
    entry = phase_map.get(phase_id)
    if entry is None:
        entry = {
            "phase_id": phase_id,
            "short_term": {"messages": [], "summaries": []},
            "semantic": [],
            "profile": [],
        }
        phase_map[phase_id] = entry
    return entry


def _phase_id_for_item(item: MemoryItem) -> str:
    meta = item.meta or {}
    value = meta.get("phase_id")
    return str(value) if value else "phase-unknown"


def _sorted_map(value: dict) -> dict:
    return {key: value[key] for key in sorted(value.keys(), key=lambda entry: str(entry))}


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


__all__ = ["build_snapshot_payload", "serialize_snapshot", "write_snapshot"]
