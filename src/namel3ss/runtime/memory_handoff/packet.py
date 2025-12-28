from __future__ import annotations

from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_links import get_item_by_id
from namel3ss.runtime.memory_links.preview import preview_text


def build_packet_preview(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    item_ids: list[str],
) -> list[dict]:
    previews: list[dict] = []
    for memory_id in item_ids:
        item = get_item_by_id(short_term=short_term, semantic=semantic, profile=profile, memory_id=memory_id)
        if item is None:
            previews.append(
                {
                    "memory_id": memory_id,
                    "kind": "unknown",
                    "event_type": "unknown",
                    "preview": "missing item",
                }
            )
            continue
        meta = item.meta or {}
        previews.append(
            {
                "memory_id": item.id,
                "kind": item.kind.value,
                "event_type": meta.get("event_type") or "unknown",
                "lane": meta.get("lane") or "unknown",
                "agent_id": meta.get("agent_id"),
                "preview": preview_text(item.text),
            }
        )
    return previews


__all__ = ["build_packet_preview"]
