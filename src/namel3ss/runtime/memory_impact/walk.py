from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from namel3ss.runtime.memory.contract import MEMORY_SCOPE_SESSION, MemoryItem, MemoryKind
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_links.model import link_sort_key
from namel3ss.runtime.memory_links.preview import preview_text
from namel3ss.runtime.memory_impact.model import ImpactItem, ImpactResult
from namel3ss.runtime.memory_impact.rules import impact_sort_key, link_direction, IMPACT_LINK_TYPES


@dataclass(frozen=True)
class ImpactRequest:
    memory_id: str
    depths: tuple[int, ...]
    max_items: int


@dataclass(frozen=True)
class _ImpactEdge:
    to_id: str
    reason: str
    preview: str


def impact_request_from_state(state: Mapping[str, object] | None) -> ImpactRequest | None:
    if not isinstance(state, Mapping):
        return None
    memory_id = state.get("_memory_impact_id")
    if not memory_id:
        return None
    depth_value = state.get("_memory_impact_depth")
    max_items = _parse_int(state.get("_memory_impact_max_items"), default=10)
    depths = _parse_depths(depth_value)
    return ImpactRequest(memory_id=str(memory_id), depths=depths, max_items=max_items)


def compute_impact(
    *,
    memory_id: str,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    depth_limit: int = 2,
    max_items: int = 10,
    root_item: MemoryItem | None = None,
) -> ImpactResult:
    if max_items <= 0:
        return ImpactResult(title="Memory impact", items=[])
    items_by_id = _collect_items(short_term, semantic, profile)
    if root_item and root_item.id not in items_by_id:
        items_by_id[root_item.id] = root_item
    adjacency = _build_adjacency(items_by_id.values())
    root_id = str(memory_id)
    visited = {root_id}
    queue: list[tuple[str, int]] = [(root_id, 0)]
    parents: dict[str, str] = {}
    reasons: dict[str, str] = {}
    previews: dict[str, str] = {}
    depths: dict[str, int] = {}

    while queue:
        current_id, depth = queue.pop(0)
        if depth >= depth_limit:
            continue
        for edge in adjacency.get(current_id, []):
            if edge.to_id in visited:
                continue
            next_depth = depth + 1
            visited.add(edge.to_id)
            parents[edge.to_id] = current_id
            reasons[edge.to_id] = edge.reason
            previews[edge.to_id] = edge.preview
            depths[edge.to_id] = next_depth
            queue.append((edge.to_id, next_depth))

    items: list[ImpactItem] = []
    for impacted_id, depth in depths.items():
        if impacted_id == root_id:
            continue
        item = items_by_id.get(impacted_id)
        items.append(
            _impact_item_for(
                impacted_id,
                depth=depth,
                reason=reasons.get(impacted_id, "impact"),
                parent_id=parents.get(impacted_id),
                item=item,
                preview=previews.get(impacted_id, ""),
            )
        )
    items.sort(key=lambda entry: impact_sort_key(entry.phase_id, entry.space, entry.memory_id))
    if len(items) > max_items:
        items = items[:max_items]
    return ImpactResult(title="Memory impact", items=items)


def _collect_items(
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
) -> dict[str, MemoryItem]:
    items: dict[str, MemoryItem] = {}
    all_items = list(_iter_items(short_term.all_items(), semantic.all_items(), profile.all_items()))
    for entry in all_items:
        items[entry.id] = entry
    for entry in _ledger_items(all_items):
        if entry.id not in items:
            items[entry.id] = entry
    return items


def _iter_items(*groups: Iterable[MemoryItem]) -> Iterable[MemoryItem]:
    for group in groups:
        for item in group:
            yield item


def _ledger_items(items: Iterable[MemoryItem]) -> list[MemoryItem]:
    ledger_items: list[MemoryItem] = []
    seen: set[str] = set()
    for item in items:
        meta = item.meta or {}
        ledger = meta.get("compaction_ledger")
        if not isinstance(ledger, list):
            continue
        for entry in ledger:
            if not isinstance(entry, dict):
                continue
            memory_id = entry.get("memory_id")
            if not isinstance(memory_id, str) or not memory_id:
                continue
            if memory_id in seen:
                continue
            seen.add(memory_id)
            ledger_items.append(_item_from_ledger(entry))
    ledger_items.sort(key=lambda entry: entry.id)
    return ledger_items


def _item_from_ledger(entry: dict) -> MemoryItem:
    kind_value = entry.get("kind") or MemoryKind.SEMANTIC.value
    kind = MemoryKind.SEMANTIC
    for candidate in MemoryKind:
        if candidate.value == kind_value:
            kind = candidate
            break
    preview = entry.get("preview") or ""
    meta = _meta_from_ledger(entry)
    return MemoryItem(
        id=str(entry.get("memory_id")),
        kind=kind,
        text=str(preview),
        source="system",
        created_at=0,
        importance=0,
        scope=MEMORY_SCOPE_SESSION,
        meta=meta,
    )


def _meta_from_ledger(entry: dict) -> dict:
    meta = {
        "space": entry.get("space") or "unknown",
        "owner": entry.get("owner") or "unknown",
        "lane": entry.get("lane") or "unknown",
        "phase_id": entry.get("phase_id") or "phase-unknown",
    }
    links = entry.get("links")
    if isinstance(links, list):
        meta["links"] = links
    previews = entry.get("link_preview_text")
    if isinstance(previews, dict):
        cleaned = {str(key): str(value) for key, value in previews.items() if isinstance(value, str)}
        if cleaned:
            meta["link_preview_text"] = cleaned
    return meta


def _links_for_item(item: MemoryItem) -> list[dict]:
    meta = item.meta or {}
    links = meta.get("links")
    if not isinstance(links, list):
        return []
    cleaned: list[dict] = []
    for entry in links:
        if isinstance(entry, dict):
            cleaned.append(dict(entry))
    cleaned.sort(key=link_sort_key)
    return cleaned


def _preview_map(item: MemoryItem) -> dict[str, str]:
    meta = item.meta or {}
    preview = meta.get("link_preview_text")
    if isinstance(preview, dict):
        return {str(key): str(value) for key, value in preview.items() if isinstance(value, str)}
    return {}


def _build_adjacency(items: Iterable[MemoryItem]) -> dict[str, list[_ImpactEdge]]:
    adjacency: dict[str, list[_ImpactEdge]] = {}
    ordered = sorted(items, key=lambda entry: entry.id)
    for item in ordered:
        preview_map = _preview_map(item)
        for link in _links_for_item(item):
            link_type = link.get("type")
            if link_type not in IMPACT_LINK_TYPES:
                continue
            target_id = link.get("to_id")
            if not isinstance(target_id, str) or not target_id:
                continue
            if target_id == item.id:
                continue
            reason = str(link.get("reason_code") or link_type)
            direction = link_direction(str(link_type))
            if direction in {"forward", "both"}:
                preview = preview_map.get(target_id) or ""
                adjacency.setdefault(item.id, []).append(
                    _ImpactEdge(to_id=target_id, reason=reason, preview=preview)
                )
            if direction in {"reverse", "both"}:
                reverse_preview = preview_text(item.text)
                adjacency.setdefault(target_id, []).append(
                    _ImpactEdge(to_id=item.id, reason=reason, preview=reverse_preview)
                )
    return adjacency


def _impact_item_for(
    memory_id: str,
    *,
    depth: int,
    reason: str,
    parent_id: Optional[str],
    item: MemoryItem | None,
    preview: str,
) -> ImpactItem:
    if item:
        meta = item.meta or {}
        space = str(meta.get("space") or "unknown")
        phase_id = str(meta.get("phase_id") or "phase-unknown")
        short_text = preview_text(item.text)
    else:
        space = "unknown"
        phase_id = "phase-unknown"
        short_text = preview
    if not short_text:
        short_text = "unknown"
    return ImpactItem(
        memory_id=str(memory_id),
        short_text=short_text,
        space=space,
        phase_id=phase_id,
        depth=int(depth),
        reason=str(reason),
        parent_id=parent_id,
    )


def _parse_depths(value: object) -> tuple[int, ...]:
    depth = _parse_int(value, default=None)
    if depth is None:
        return (1, 2)
    if depth < 1:
        depth = 1
    if depth > 2:
        depth = 2
    return (depth,)


def _parse_int(value: object, *, default: int | None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = ["ImpactRequest", "compute_impact", "impact_request_from_state"]
