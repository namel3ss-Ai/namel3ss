from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry


@dataclass(frozen=True)
class BudgetUsage:
    store_key: str
    space: str
    owner: str
    lane: str
    phase_id: str
    short_term_count: int
    semantic_count: int
    profile_count: int
    total_count: int
    max_links_count: int
    phase_count: int


def measure_budget_usage(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    phase_registry: PhaseRegistry,
) -> list[BudgetUsage]:
    counts = _count_items(short_term, semantic, profile)
    usage: list[BudgetUsage] = []
    phase_counts = {store_key: len(phase_registry.phases(store_key)) for store_key in _store_keys_from_counts(counts)}
    for (store_key, phase_id), entry in counts.items():
        space, owner, lane = _parse_store_key(store_key)
        total = entry["short_term"] + entry["semantic"] + entry["profile"]
        usage.append(
            BudgetUsage(
                store_key=store_key,
                space=space,
                owner=owner,
                lane=lane,
                phase_id=phase_id,
                short_term_count=entry["short_term"],
                semantic_count=entry["semantic"],
                profile_count=entry["profile"],
                total_count=total,
                max_links_count=entry["max_links"],
                phase_count=phase_counts.get(store_key, 0),
            )
        )
    usage.sort(key=lambda entry: (entry.store_key, entry.phase_id))
    return usage


def usage_for_scope(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    phase_registry: PhaseRegistry,
    store_key: str,
    phase_id: str,
) -> BudgetUsage:
    counts = _count_items(short_term, semantic, profile)
    entry = counts.get((store_key, phase_id))
    if entry is None:
        entry = {"short_term": 0, "semantic": 0, "profile": 0, "max_links": 0}
    space, owner, lane = _parse_store_key(store_key)
    total = entry["short_term"] + entry["semantic"] + entry["profile"]
    phase_count = len(phase_registry.phases(store_key))
    return BudgetUsage(
        store_key=store_key,
        space=space,
        owner=owner,
        lane=lane,
        phase_id=phase_id,
        short_term_count=entry["short_term"],
        semantic_count=entry["semantic"],
        profile_count=entry["profile"],
        total_count=total,
        max_links_count=entry["max_links"],
        phase_count=phase_count,
    )


def _count_items(
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
) -> dict[tuple[str, str], dict[str, int]]:
    counts: dict[tuple[str, str], dict[str, int]] = {}
    for item in _iter_items(short_term.all_items(), semantic.all_items(), profile.all_items()):
        store_key = _store_key_from_id(item.id)
        if not store_key:
            continue
        phase_id = _phase_id_for(item)
        key = (store_key, phase_id)
        entry = counts.setdefault(key, {"short_term": 0, "semantic": 0, "profile": 0, "max_links": 0})
        if item.kind.value == "short_term":
            entry["short_term"] += 1
        elif item.kind.value == "semantic":
            entry["semantic"] += 1
        elif item.kind.value == "profile":
            entry["profile"] += 1
        link_count = _link_count(item)
        if link_count > entry["max_links"]:
            entry["max_links"] = link_count
    return counts


def _iter_items(*groups: list[MemoryItem]) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    for group in groups:
        items.extend(group)
    items.sort(key=lambda entry: entry.id)
    return items


def _store_keys_from_counts(counts: dict[tuple[str, str], dict[str, int]]) -> list[str]:
    keys = {store_key for store_key, _ in counts.keys()}
    return sorted(keys)


def _store_key_from_id(memory_id: str) -> str | None:
    if not isinstance(memory_id, str):
        return None
    parts = memory_id.split(":")
    if len(parts) < 3:
        return None
    return ":".join(parts[:-2])


def _parse_store_key(store_key: str) -> tuple[str, str, str]:
    parts = store_key.split(":") if isinstance(store_key, str) else []
    if len(parts) < 3:
        return "unknown", "unknown", "unknown"
    space = parts[0]
    owner = parts[1]
    lane = ":".join(parts[2:])
    return space, owner, lane


def _phase_id_for(item: MemoryItem) -> str:
    meta = item.meta or {}
    phase_id = meta.get("phase_id")
    if isinstance(phase_id, str) and phase_id:
        return phase_id
    return "phase-unknown"


def _link_count(item: MemoryItem) -> int:
    meta = item.meta or {}
    links = meta.get("links")
    if isinstance(links, list):
        return len(links)
    return 0


__all__ = ["BudgetUsage", "measure_budget_usage", "usage_for_scope"]
