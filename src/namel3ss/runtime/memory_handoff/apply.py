from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import ensure_space_meta
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM, ensure_lane_meta
from namel3ss.runtime.memory_links import get_item_by_id
from namel3ss.runtime.memory_links.preview import preview_text
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta

from namel3ss.runtime.memory_handoff.model import HandoffPacket


def apply_handoff_packet(
    *,
    packet: HandoffPacket,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    target_store_key: str,
    target_phase,
    space: str,
    owner: str,
    agent_id: str,
    allow_team_change: bool,
    phase_ledger: PhaseLedger,
    dedupe_enabled: bool,
    authority_order: list[str],
) -> list[MemoryItem]:
    applied: list[MemoryItem] = []
    for memory_id in packet.items:
        original = get_item_by_id(short_term=short_term, semantic=semantic, profile=profile, memory_id=memory_id)
        if original is None:
            continue
        lane = original.meta.get("lane") if original.meta else None
        if lane not in {LANE_AGENT, LANE_TEAM}:
            continue
        meta = _handoff_meta(
            original,
            packet=packet,
            space=space,
            owner=owner,
            agent_id=agent_id,
            allow_team_change=allow_team_change,
            target_phase=target_phase,
        )
        copied = factory.create(
            session=target_store_key,
            kind=original.kind,
            text=original.text,
            source=original.source,
            importance=original.importance,
            meta=meta,
        )
        stored = _store_item(
            short_term=short_term,
            semantic=semantic,
            profile=profile,
            item=copied,
            store_key=target_store_key,
            dedupe_enabled=dedupe_enabled,
            authority_order=authority_order,
        )
        if stored is None:
            continue
        applied.append(stored)
        if target_phase:
            phase_ledger.record_add(target_store_key, phase=target_phase, item=stored)
    return applied


def _handoff_meta(
    item: MemoryItem,
    *,
    packet: HandoffPacket,
    space: str,
    owner: str,
    agent_id: str,
    allow_team_change: bool,
    target_phase,
) -> dict:
    meta = dict(item.meta or {})
    meta = ensure_space_meta(meta, space=space, owner=owner)
    meta.pop("lane", None)
    meta.pop("visible_to", None)
    meta.pop("can_change", None)
    meta.pop("agent_id", None)
    meta = ensure_lane_meta(meta, lane=LANE_AGENT, allow_team_change=allow_team_change, agent_id=agent_id)
    meta = apply_phase_meta(meta, target_phase)
    meta["handoff_packet_id"] = packet.packet_id
    meta["handoff_from_agent"] = packet.from_agent_id
    meta["handoff_to_agent"] = packet.to_agent_id
    previews = _link_previews(item)
    if previews:
        meta["handoff_link_previews"] = previews
    meta.pop("links", None)
    meta.pop("link_preview_text", None)
    return meta


def _link_previews(item: MemoryItem) -> list[str]:
    meta = item.meta or {}
    links = meta.get("links")
    if not isinstance(links, list):
        return []
    preview_map = meta.get("link_preview_text") if isinstance(meta.get("link_preview_text"), dict) else {}
    previews: list[str] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        to_id = link.get("to_id")
        preview = preview_map.get(to_id) if to_id else None
        if preview:
            previews.append(preview_text(preview))
        else:
            previews.append("Linked item preview is missing.")
    return previews


def _store_item(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    item: MemoryItem,
    store_key: str,
    dedupe_enabled: bool,
    authority_order: list[str],
) -> MemoryItem | None:
    if item.kind == MemoryKind.SHORT_TERM:
        short_term.store_item(store_key, item)
        return item
    if item.kind == MemoryKind.SEMANTIC:
        stored, _conflict, _deleted = semantic.store_item(
            store_key,
            item,
            dedupe_enabled=dedupe_enabled,
            authority_order=authority_order,
        )
        return stored
    if item.kind == MemoryKind.PROFILE:
        stored, _conflict, _deleted = profile.store_item(
            store_key,
            item,
            dedupe_enabled=dedupe_enabled,
            authority_order=authority_order,
        )
        return stored
    return None


__all__ = ["apply_handoff_packet"]
