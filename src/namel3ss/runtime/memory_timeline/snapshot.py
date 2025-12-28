from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_timeline.phase import PhaseInfo


@dataclass(frozen=True)
class SnapshotItem:
    memory_id: str
    kind: str
    dedupe_key: str | None


@dataclass
class PhaseSnapshot:
    phase_id: str
    phase_index: int
    items: dict[str, SnapshotItem]
    dedupe_map: dict[str, str]

    def copy_for(self, phase: PhaseInfo) -> PhaseSnapshot:
        return PhaseSnapshot(
            phase_id=phase.phase_id,
            phase_index=phase.phase_index,
            items=dict(self.items),
            dedupe_map=dict(self.dedupe_map),
        )


class PhaseLedger:
    def __init__(self) -> None:
        self._snapshots: dict[str, dict[str, PhaseSnapshot]] = {}
        self._order: dict[str, list[str]] = {}

    def start_phase(self, store_key: str, *, phase: PhaseInfo, previous: PhaseInfo | None) -> PhaseSnapshot:
        snapshots = self._snapshots.setdefault(store_key, {})
        order = self._order.setdefault(store_key, [])
        if phase.phase_id in snapshots:
            return snapshots[phase.phase_id]
        if previous and previous.phase_id in snapshots:
            snapshot = snapshots[previous.phase_id].copy_for(phase)
        else:
            snapshot = PhaseSnapshot(phase.phase_id, phase.phase_index, items={}, dedupe_map={})
        snapshots[phase.phase_id] = snapshot
        order.append(phase.phase_id)
        return snapshot

    def snapshot(self, store_key: str, phase_id: str) -> PhaseSnapshot | None:
        return self._snapshots.get(store_key, {}).get(phase_id)

    def phase_ids(self, store_key: str) -> list[str]:
        return list(self._order.get(store_key, []))

    def record_add(self, store_key: str, *, phase: PhaseInfo, item: MemoryItem) -> None:
        snapshot = self._ensure_snapshot(store_key, phase)
        dedupe_key = _dedupe_key(item)
        snapshot.items[item.id] = SnapshotItem(item.id, _kind_value(item), dedupe_key)
        if dedupe_key:
            snapshot.dedupe_map[dedupe_key] = item.id

    def record_delete(self, store_key: str, *, phase: PhaseInfo, memory_id: str) -> None:
        snapshot = self._ensure_snapshot(store_key, phase)
        item = snapshot.items.pop(memory_id, None)
        if item and item.dedupe_key:
            if snapshot.dedupe_map.get(item.dedupe_key) == memory_id:
                snapshot.dedupe_map.pop(item.dedupe_key, None)

    def cleanup(self, store_key: str, max_phases: int | None) -> None:
        if not max_phases:
            return
        order = self._order.get(store_key, [])
        if len(order) <= max_phases:
            return
        excess = len(order) - max_phases
        to_remove = order[:excess]
        self._order[store_key] = order[excess:]
        snapshots = self._snapshots.get(store_key, {})
        for phase_id in to_remove:
            snapshots.pop(phase_id, None)

    def _ensure_snapshot(self, store_key: str, phase: PhaseInfo) -> PhaseSnapshot:
        snapshots = self._snapshots.setdefault(store_key, {})
        snapshot = snapshots.get(phase.phase_id)
        if snapshot is None:
            snapshot = PhaseSnapshot(phase.phase_id, phase.phase_index, items={}, dedupe_map={})
            snapshots[phase.phase_id] = snapshot
            self._order.setdefault(store_key, []).append(phase.phase_id)
        return snapshot


def _dedupe_key(item: MemoryItem) -> str | None:
    meta = item.meta or {}
    key = meta.get("dedup_key")
    return str(key) if key else None


def _kind_value(item: MemoryItem) -> str:
    kind = item.kind
    if hasattr(kind, "value"):
        return kind.value
    return str(kind)


__all__ = ["PhaseLedger", "PhaseSnapshot", "SnapshotItem"]
