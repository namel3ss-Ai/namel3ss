from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_DECISION
from namel3ss.runtime.memory_lanes.model import LANE_SYSTEM, LANE_TEAM
from namel3ss.runtime.memory_agreement.model import AGREEMENT_APPROVED, AGREEMENT_PENDING
from namel3ss.runtime.memory_links.model import link_sort_key


@dataclass(frozen=True)
class CompactionSelection:
    items: list[MemoryItem]
    reason_codes: list[str]


def select_compaction_items(
    items: list[MemoryItem],
    *,
    phase_id: str,
    target: str,
    max_remove: int,
    allow_delete_approved: bool = False,
    keep_recent_short_term: int = 2,
) -> CompactionSelection:
    if max_remove <= 0:
        return CompactionSelection(items=[], reason_codes=[])
    scoped = _filter_scope(items, phase_id=phase_id, target=target)
    if not scoped:
        return CompactionSelection(items=[], reason_codes=[])
    inbound = _inbound_links(items)
    ordered_short_term = _order_short_term(scoped)
    candidates: list[tuple[MemoryItem, list[str]]] = []
    for item in scoped:
        if _is_protected(item, allow_delete_approved=allow_delete_approved):
            continue
        reasons = _low_value_reasons(
            item,
            inbound_links=inbound.get(item.id, 0),
            old_short_term=_is_old_short_term(item, ordered_short_term, keep_recent=keep_recent_short_term),
        )
        if reasons:
            candidates.append((item, reasons))
    candidates.sort(key=lambda pair: (pair[0].created_at, pair[0].id))
    selected = candidates[:max_remove]
    reason_codes = sorted({code for _, reasons in selected for code in reasons})
    return CompactionSelection(items=[item for item, _ in selected], reason_codes=reason_codes)


def _filter_scope(items: list[MemoryItem], *, phase_id: str, target: str) -> list[MemoryItem]:
    filtered: list[MemoryItem] = []
    for item in items:
        if _phase_id(item) != phase_id:
            continue
        if target in {"short_term", "semantic", "profile"}:
            if item.kind.value != target:
                continue
        filtered.append(item)
    return filtered


def _low_value_reasons(
    item: MemoryItem,
    *,
    inbound_links: int,
    old_short_term: bool,
) -> list[str]:
    meta = item.meta or {}
    reasons: list[str] = []
    if meta.get("event_type") == EVENT_CONTEXT:
        reasons.append("context")
    if item.importance <= 1:
        reasons.append("low_importance")
    if item.kind.value == "short_term" and old_short_term:
        reasons.append("old_turn")
    if _link_count(item) == 0 and inbound_links == 0:
        reasons.append("no_links")
    return reasons


def _is_protected(item: MemoryItem, *, allow_delete_approved: bool) -> bool:
    meta = item.meta or {}
    lane = meta.get("lane")
    event_type = meta.get("event_type")
    if lane == LANE_SYSTEM:
        return True
    if meta.get("rule") and lane == LANE_SYSTEM:
        return True
    if lane == LANE_TEAM and event_type == EVENT_DECISION:
        return True
    status = meta.get("agreement_status")
    if status == AGREEMENT_PENDING:
        return True
    if status == AGREEMENT_APPROVED and not allow_delete_approved:
        return True
    if meta.get("summary_of") or meta.get("compaction_ledger"):
        return True
    return False


def _inbound_links(items: list[MemoryItem]) -> dict[str, int]:
    inbound: dict[str, int] = {}
    ordered = sorted(items, key=lambda entry: entry.id)
    for item in ordered:
        for link in _links_for_item(item):
            target = link.get("to_id")
            if not isinstance(target, str) or not target:
                continue
            inbound[target] = inbound.get(target, 0) + 1
    return inbound


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


def _order_short_term(items: list[MemoryItem]) -> list[MemoryItem]:
    short_term = [item for item in items if item.kind.value == "short_term"]
    short_term.sort(key=lambda entry: (entry.created_at, entry.id))
    return short_term


def _is_old_short_term(item: MemoryItem, ordered: list[MemoryItem], *, keep_recent: int) -> bool:
    if item.kind.value != "short_term":
        return False
    if keep_recent <= 0:
        return True
    if len(ordered) <= keep_recent:
        return False
    recent = {entry.id for entry in ordered[-keep_recent:]}
    return item.id not in recent


def _phase_id(item: MemoryItem) -> str:
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


__all__ = ["CompactionSelection", "select_compaction_items"]
