from __future__ import annotations

from namel3ss.runtime.memory.contract import normalize_memory_item
from namel3ss.runtime.memory.manager import MemoryManager


def _snapshot_memory_items(manager: MemoryManager) -> dict[str, dict]:
    items: dict[str, dict] = {}
    for item in manager.short_term.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    for item in manager.semantic.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    for item in manager.profile.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    return items


def _delta_written(before: dict[str, dict], after: dict[str, dict]) -> list[dict]:
    added: list[dict] = []
    for memory_id, item in after.items():
        if memory_id not in before:
            added.append(item)
    added.sort(key=lambda entry: entry.get("id") or "")
    return added


def _cache_versions(manager: MemoryManager) -> list[dict]:
    versions: list[dict] = []
    for (store_key, kind), version in getattr(manager, "_cache_versions", {}).items():
        versions.append({"store_key": str(store_key), "kind": str(kind), "version": int(version)})
    versions.sort(key=lambda entry: (entry["store_key"], entry["kind"]))
    return versions


def _phase_snapshot(manager: MemoryManager) -> list[dict]:
    phases: list[dict] = []
    registry = getattr(manager, "_phases", None)
    if registry is None:
        return phases
    current_map = getattr(registry, "_current", {})
    history_map = getattr(registry, "_history", {})
    for store_key, current in current_map.items():
        history = history_map.get(store_key, [])
        phases.append(
            {
                "store_key": store_key,
                "current_phase_id": current.phase_id if current else None,
                "history_ids": [phase.phase_id for phase in history],
            }
        )
    phases.sort(key=lambda entry: entry["store_key"])
    return phases


def _memory_counts(manager: MemoryManager) -> dict:
    return {
        "short_term": len(manager.short_term.all_items()),
        "semantic": len(manager.semantic.all_items()),
        "profile": len(manager.profile.all_items()),
    }


__all__ = [
    "_cache_versions",
    "_delta_written",
    "_memory_counts",
    "_phase_snapshot",
    "_snapshot_memory_items",
]
