from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory.helpers import authority_for_source, build_meta
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory_links import (
    LINK_TYPE_REPLACED,
    add_link_to_item,
    build_link_record,
    build_preview_for_item,
)
from namel3ss.runtime.memory_links.model import LINK_LIMIT
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger

from .summarize import CompactionSummary
from .select import CompactionSelection


@dataclass(frozen=True)
class CompactionResult:
    removed: list[MemoryItem]
    summary_item: MemoryItem | None


def apply_compaction(
    *,
    selection: CompactionSelection,
    summary: CompactionSummary | None,
    factory: MemoryItemFactory,
    store_key: str,
    space: str,
    owner: str,
    lane: str,
    phase,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    phase_ledger: PhaseLedger,
    max_links_per_item: int | None = None,
) -> CompactionResult:
    if not selection.items:
        return CompactionResult(removed=[], summary_item=None)
    removed = _remove_items(selection.items, store_key, short_term, semantic, profile, phase_ledger, phase)
    summary_item = None
    if summary is not None:
        summary_item = _build_summary_item(
            selection=selection,
            summary=summary,
            factory=factory,
            store_key=store_key,
            space=space,
            owner=owner,
            lane=lane,
            phase=phase,
            max_links_per_item=max_links_per_item,
        )
        if summary_item:
            summary_item = _store_summary(summary_item, store_key, short_term, semantic)
            if summary_item:
                phase_ledger.record_add(store_key, phase=phase, item=summary_item)
    return CompactionResult(removed=removed, summary_item=summary_item)


def _remove_items(
    items: list[MemoryItem],
    store_key: str,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    phase_ledger: PhaseLedger,
    phase,
) -> list[MemoryItem]:
    removed: list[MemoryItem] = []
    ordered = sorted(items, key=lambda entry: entry.id)
    for item in ordered:
        deleted = None
        if item.kind == MemoryKind.SHORT_TERM:
            deleted = short_term.delete_item(store_key, item.id)
        elif item.kind == MemoryKind.SEMANTIC:
            deleted = semantic.delete_item(store_key, item.id)
        elif item.kind == MemoryKind.PROFILE:
            deleted = profile.delete_item(store_key, item.id)
        if deleted:
            removed.append(deleted)
            phase_ledger.record_delete(store_key, phase=phase, memory_id=deleted.id)
    return removed


def _build_summary_item(
    *,
    selection: CompactionSelection,
    summary: CompactionSummary,
    factory: MemoryItemFactory,
    store_key: str,
    space: str,
    owner: str,
    lane: str,
    phase,
    max_links_per_item: int | None,
) -> MemoryItem:
    importance, reasons = importance_for_event(EVENT_CONTEXT, summary.text, "system")
    reasons.append("compaction")
    authority, authority_reason = authority_for_source("system")
    meta = build_meta(
        EVENT_CONTEXT,
        reasons,
        summary.text,
        authority=authority,
        authority_reason=authority_reason,
        space=space,
        owner=owner,
        lane=lane,
        phase=phase,
    )
    meta["summary_of"] = [item.id for item in selection.items]
    meta["compaction_ledger"] = list(summary.ledger)
    if selection.reason_codes:
        meta["compaction_reason_codes"] = list(selection.reason_codes)
    summary_kind = _summary_kind(selection.items)
    summary_item = factory.create(
        session=store_key,
        kind=summary_kind,
        text=summary.text,
        source="system",
        importance=importance,
        meta=meta,
    )
    max_links = max_links_per_item if max_links_per_item is not None else LINK_LIMIT
    for item in selection.items:
        summary_item = _add_summary_link(summary_item, item, phase_id=getattr(phase, "phase_id", "phase-unknown"), max_links=max_links)
    return summary_item


def _summary_kind(items: list[MemoryItem]) -> MemoryKind:
    kinds = {item.kind for item in items}
    if len(kinds) == 1:
        kind = next(iter(kinds))
        if kind == MemoryKind.PROFILE:
            return MemoryKind.SEMANTIC
        return kind
    return MemoryKind.SEMANTIC


def _add_summary_link(item: MemoryItem, target: MemoryItem, *, phase_id: str, max_links: int) -> MemoryItem:
    link = build_link_record(
        link_type=LINK_TYPE_REPLACED,
        to_id=target.id,
        reason_code="compacted",
        created_in_phase_id=phase_id,
    )
    preview = build_preview_for_item(target)
    return add_link_to_item(item, link, preview=preview, max_links=max_links)


def _store_summary(
    item: MemoryItem,
    store_key: str,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
) -> MemoryItem | None:
    if item.kind == MemoryKind.SHORT_TERM:
        short_term.store_item(store_key, item)
        return item
    if item.kind == MemoryKind.SEMANTIC:
        stored, _conflict, _deleted = semantic.store_item(store_key, item, dedupe_enabled=False)
        return stored or item
    return item


__all__ = ["CompactionResult", "apply_compaction"]
