from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger, SnapshotItem


@dataclass(frozen=True)
class PhaseDiff:
    from_phase_id: str
    to_phase_id: str
    added: list[SnapshotItem]
    deleted: list[SnapshotItem]
    replaced: list[tuple[SnapshotItem, SnapshotItem, str]]

    def summary_lines(self) -> list[str]:
        return [
            f"Added {len(self.added)} items",
            f"Deleted {len(self.deleted)} items",
            f"Replaced {len(self.replaced)} items",
        ]

    def top_changes(self, *, limit: int = 8) -> list[dict]:
        changes: list[dict] = []
        for before, after, key in self.replaced:
            changes.append(
                {
                    "change": "replaced",
                    "dedupe_key": key,
                    "from_id": before.memory_id,
                    "to_id": after.memory_id,
                    "from_kind": before.kind,
                    "to_kind": after.kind,
                }
            )
        for item in self.added:
            changes.append({"change": "added", "memory_id": item.memory_id, "kind": item.kind})
        for item in self.deleted:
            changes.append({"change": "deleted", "memory_id": item.memory_id, "kind": item.kind})
        changes.sort(key=_change_sort_key)
        return changes[:limit]


@dataclass(frozen=True)
class PhaseDiffRequest:
    from_phase_id: str
    to_phase_id: str
    space: str
    lane: str


def diff_phases(ledger: PhaseLedger, *, store_key: str, from_phase_id: str, to_phase_id: str) -> PhaseDiff:
    from_snapshot = ledger.snapshot(store_key, from_phase_id)
    to_snapshot = ledger.snapshot(store_key, to_phase_id)
    if not from_snapshot or not to_snapshot:
        return PhaseDiff(from_phase_id, to_phase_id, added=[], deleted=[], replaced=[])
    from_ids = set(from_snapshot.items.keys())
    to_ids = set(to_snapshot.items.keys())
    added_ids = to_ids - from_ids
    deleted_ids = from_ids - to_ids
    replaced = _replacements(from_snapshot.dedupe_map, to_snapshot.dedupe_map, from_snapshot.items, to_snapshot.items)
    replaced_from = {before.memory_id for before, _, _ in replaced}
    replaced_to = {after.memory_id for _, after, _ in replaced}
    added = sorted(
        [to_snapshot.items[item_id] for item_id in added_ids if item_id not in replaced_to],
        key=lambda item: item.memory_id,
    )
    deleted = sorted(
        [from_snapshot.items[item_id] for item_id in deleted_ids if item_id not in replaced_from],
        key=lambda item: item.memory_id,
    )
    return PhaseDiff(from_phase_id, to_phase_id, added=added, deleted=deleted, replaced=replaced)


def phase_diff_request_from_state(state: Mapping[str, object] | None) -> PhaseDiffRequest | None:
    if not isinstance(state, dict):
        return None
    from_phase = state.get("_memory_phase_diff_from")
    to_phase = state.get("_memory_phase_diff_to")
    if not from_phase or not to_phase:
        return None
    space = state.get("_memory_phase_diff_space") or "session"
    lane = state.get("_memory_phase_diff_lane") or "my"
    return PhaseDiffRequest(
        from_phase_id=str(from_phase),
        to_phase_id=str(to_phase),
        space=str(space),
        lane=str(lane),
    )


def _replacements(
    from_map: dict[str, str],
    to_map: dict[str, str],
    from_items: dict[str, SnapshotItem],
    to_items: dict[str, SnapshotItem],
) -> list[tuple[SnapshotItem, SnapshotItem, str]]:
    replaced: list[tuple[SnapshotItem, SnapshotItem, str]] = []
    shared_keys = sorted(set(from_map.keys()) & set(to_map.keys()))
    for key in shared_keys:
        from_id = from_map[key]
        to_id = to_map[key]
        if from_id == to_id:
            continue
        before = from_items.get(from_id)
        after = to_items.get(to_id)
        if before and after:
            replaced.append((before, after, key))
    return replaced


def _change_sort_key(entry: dict) -> tuple:
    change_order = {"replaced": 0, "added": 1, "deleted": 2}
    change = entry.get("change", "")
    primary = change_order.get(change, 3)
    dedupe_key = entry.get("dedupe_key") or ""
    memory_id = entry.get("memory_id") or entry.get("from_id") or ""
    return (primary, str(dedupe_key), str(memory_id))


__all__ = ["PhaseDiff", "PhaseDiffRequest", "diff_phases", "phase_diff_request_from_state"]
