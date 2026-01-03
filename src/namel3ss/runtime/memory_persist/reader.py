from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_persist.format import (
    decode_budget_config,
    decode_handoff_packet,
    decode_memory_item,
    decode_phase_info,
    decode_proposal,
    decode_snapshot_item,
    decode_trust_rules,
)
from namel3ss.runtime.memory_persist.paths import snapshot_paths
from namel3ss.runtime.memory_persist.verify import verify_checksum, verify_snapshot_payload
from namel3ss.runtime.memory_agreement.store import _AgreementRecord
from namel3ss.runtime.memory_cache.store import CacheEntry
from namel3ss.runtime.memory_timeline.snapshot import PhaseSnapshot


def read_snapshot(
    *,
    project_root: str | None,
    app_path: str | None,
) -> dict | None:
    snapshot_path, checksum_path = _locate_snapshot(project_root=project_root, app_path=app_path)
    if snapshot_path is None or checksum_path is None:
        return None
    verify_checksum(snapshot_path, checksum_path)
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except JSONDecodeError as err:
        raise Namel3ssError(f"Snapshot could not be parsed: {err.msg}.") from err
    verify_snapshot_payload(payload)
    return _decode_snapshot_payload(payload)


def _locate_snapshot(*, project_root: str | None, app_path: str | None) -> tuple[Path | None, Path | None]:
    candidates = [
        snapshot_paths(
            project_root=project_root,
            app_path=app_path,
            for_write=True,
            allow_create=False,
        ),
        snapshot_paths(
            project_root=project_root,
            app_path=app_path,
            for_write=False,
        ),
    ]
    for snapshot_path, checksum_path in candidates:
        if snapshot_path is None or checksum_path is None:
            continue
        if snapshot_path.exists():
            return snapshot_path, checksum_path
    return None, None


def _decode_snapshot_payload(payload: dict) -> dict:
    phase_registry = _decode_phase_registry(payload.get("phases") or {})
    phase_ledger = _decode_phase_ledger(payload.get("ledger") or {})
    return {
        "project_id": str(payload.get("project_id")),
        "clock_tick": int(payload.get("clock", {}).get("tick", 0)),
        "id_counters": list(payload.get("ids", {}).get("counters", [])),
        "phase_registry": phase_registry,
        "phase_ledger": phase_ledger,
        "items": _decode_items(payload.get("items") or {}),
        "agreements": _decode_agreements(payload.get("agreements") or {}),
        "handoffs": _decode_handoffs(payload.get("handoffs") or {}),
        "budgets": [decode_budget_config(cfg) for cfg in payload.get("budgets") or []],
        "cache": _decode_cache(payload.get("cache") or {}),
        "cache_versions": list(payload.get("cache_versions") or []),
        "rules": dict(payload.get("rules") or {}),
        "trust": decode_trust_rules(payload.get("trust")),
    }


def _decode_phase_registry(payload: dict) -> dict:
    counters = {key: int(value) for key, value in (payload.get("counters") or {}).items()}
    current = {key: decode_phase_info(value) for key, value in (payload.get("current") or {}).items()}
    history = {
        key: [decode_phase_info(entry) for entry in entries]
        for key, entries in (payload.get("history") or {}).items()
    }
    last_token = {key: str(value) for key, value in (payload.get("last_token") or {}).items()}
    return {
        "counters": counters,
        "current": current,
        "history": history,
        "last_token": last_token,
    }


def _decode_phase_ledger(payload: dict) -> dict:
    snapshots: dict[str, dict[str, PhaseSnapshot]] = {}
    for store_key, by_phase in (payload.get("snapshots") or {}).items():
        snapshots[store_key] = {}
        for phase_id, snapshot in (by_phase or {}).items():
            snapshots[store_key][phase_id] = _decode_phase_snapshot(snapshot)
    order = {key: list(values) for key, values in (payload.get("order") or {}).items()}
    return {"snapshots": snapshots, "order": order}


def _decode_phase_snapshot(payload: dict) -> PhaseSnapshot:
    items = {key: decode_snapshot_item(value) for key, value in (payload.get("items") or {}).items()}
    dedupe_map = {key: str(value) for key, value in (payload.get("dedupe_map") or {}).items()}
    return PhaseSnapshot(
        phase_id=str(payload.get("phase_id")),
        phase_index=int(payload.get("phase_index")),
        items=items,
        dedupe_map=dedupe_map,
    )


def _decode_items(payload: dict) -> list[dict]:
    stores = []
    for store in payload.get("stores") or []:
        phases = []
        for phase in store.get("phases") or []:
            short_term = phase.get("short_term") or {}
            phases.append(
                {
                    "phase_id": str(phase.get("phase_id")),
                    "short_term_messages": [decode_memory_item(item) for item in short_term.get("messages") or []],
                    "short_term_summaries": [decode_memory_item(item) for item in short_term.get("summaries") or []],
                    "semantic": [decode_memory_item(item) for item in phase.get("semantic") or []],
                    "profile": [decode_memory_item(item) for item in phase.get("profile") or []],
                }
            )
        stores.append(
            {
                "store_key": str(store.get("store_key")),
                "space": str(store.get("space")),
                "owner": str(store.get("owner")),
                "lane": str(store.get("lane")),
                "phases": phases,
            }
        )
    return stores


def _decode_agreements(payload: dict) -> dict:
    pending = [decode_proposal(entry) for entry in payload.get("pending") or []]
    history = {}
    for team_id, records in (payload.get("history") or {}).items():
        history[team_id] = [
            _AgreementRecord(
                proposal_id=str(entry.get("proposal_id")),
                status=str(entry.get("status")),
                phase_id=str(entry.get("phase_id")),
                decided_at=int(entry.get("decided_at")),
            )
            for entry in records
        ]
    return {
        "counter": int(payload.get("counter", 0)),
        "tick": int(payload.get("tick", 0)),
        "pending": pending,
        "history": history,
    }


def _decode_handoffs(payload: dict) -> dict:
    packets = [decode_handoff_packet(entry) for entry in payload.get("packets") or []]
    return {
        "counter": int(payload.get("counter", 0)),
        "tick": int(payload.get("tick", 0)),
        "packets": packets,
    }


def _decode_cache(payload: dict) -> dict:
    entries = []
    for entry in payload.get("entries") or []:
        version = entry.get("version")
        if isinstance(version, list):
            version = tuple(version)
        entries.append(
            {
                "key": str(entry.get("key")),
                "inserted_at": int(entry.get("inserted_at", 0)),
                "version": version,
                "value": entry.get("value"),
                "cache_entry": CacheEntry(
                    value=entry.get("value"),
                    inserted_at=int(entry.get("inserted_at", 0)),
                    version=version,
                ),
            }
        )
    return {
        "max_entries": int(payload.get("max_entries", 0)),
        "counter": int(payload.get("counter", 0)),
        "entries": entries,
    }


__all__ = ["read_snapshot"]
