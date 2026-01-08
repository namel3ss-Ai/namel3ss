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
    reasons: dict[str, str] | None = None,
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
                    "category": "missing",
                    "why": "Item was not found in memory.",
                }
            )
            continue
        meta = item.meta or {}
        reason = (reasons or {}).get(item.id) if reasons else None
        previews.append(
            {
                "memory_id": item.id,
                "kind": item.kind.value,
                "event_type": meta.get("event_type") or "unknown",
                "lane": meta.get("lane") or "unknown",
                "agent_id": meta.get("agent_id"),
                "preview": preview_text(item.text),
                "category": reason or "other",
                "why": _reason_line(reason),
            }
        )
    return previews


def _reason_line(reason: str | None) -> str:
    mapping = {
        "decisions": "Selected as a decision item.",
        "proposals": "Selected as a pending proposal.",
        "conflicts": "Selected due to a conflict link.",
        "rules": "Selected as an active rule.",
        "impact": "Selected due to an impact warning.",
    }
    if reason:
        return mapping.get(reason, "Selected by handoff policy.")
    return "Selected by handoff policy."


__all__ = ["build_packet_preview"]
