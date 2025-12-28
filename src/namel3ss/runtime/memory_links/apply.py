from __future__ import annotations

from dataclasses import replace
from typing import Callable

from namel3ss.runtime.memory.contract import MemoryItem, MemoryKind
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory_links.model import LINK_LIMIT, LinkRecord
from namel3ss.runtime.memory_links.preview import preview_text


def build_link_record(
    *,
    link_type: str,
    to_id: str,
    reason_code: str,
    created_in_phase_id: str,
    source_event_id: str | None = None,
) -> LinkRecord:
    record: LinkRecord = {
        "type": link_type,
        "to_id": to_id,
        "reason_code": reason_code,
        "created_in_phase_id": created_in_phase_id,
    }
    if source_event_id:
        record["source_event_id"] = source_event_id
    return record


def add_link_to_item(
    item: MemoryItem,
    link: LinkRecord,
    *,
    preview: str | None,
    max_links: int = LINK_LIMIT,
) -> MemoryItem:
    meta = dict(item.meta or {})
    existing_links = _normalize_links(meta.get("links"))
    if _link_exists(existing_links, link):
        return item
    existing_links.append(link)
    trimmed, preview_map = _apply_link_limit(existing_links, meta.get("link_preview_text"), max_links=max_links)
    if preview:
        preview_map[link.get("to_id") or ""] = preview
    if trimmed:
        meta["links"] = trimmed
    else:
        meta.pop("links", None)
    if preview_map:
        meta["link_preview_text"] = preview_map
    else:
        meta.pop("link_preview_text", None)
    return replace(item, meta=meta)


def build_preview_for_item(item: MemoryItem) -> str:
    return preview_text(item.text)


def build_preview_for_tool(tool_name: str) -> str:
    return preview_text(f"tool call {tool_name}")


class LinkTracker:
    def __init__(
        self,
        *,
        short_term: ShortTermMemory,
        semantic: SemanticMemory,
        profile: ProfileMemory,
        max_links: int = LINK_LIMIT,
    ) -> None:
        self._short_term = short_term
        self._semantic = semantic
        self._profile = profile
        self._max_links = max_links
        self._updated: dict[str, MemoryItem] = {}

    def add_link(
        self,
        *,
        from_id: str,
        link: LinkRecord,
        preview: str | None,
    ) -> MemoryItem | None:
        updated = update_item_by_id(
            short_term=self._short_term,
            semantic=self._semantic,
            profile=self._profile,
            memory_id=from_id,
            updater=lambda item: add_link_to_item(item, link, preview=preview, max_links=self._max_links),
        )
        if updated:
            self._updated[from_id] = updated
        return updated

    def updated_items(self) -> dict[str, MemoryItem]:
        return dict(self._updated)


def update_item_by_id(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    memory_id: str,
    updater: Callable[[MemoryItem], MemoryItem],
) -> MemoryItem | None:
    parsed = _parse_memory_id(memory_id)
    if parsed is None:
        return None
    store_key, kind = parsed
    if kind == MemoryKind.SHORT_TERM.value:
        return short_term.update_item(store_key, memory_id, updater)
    if kind == MemoryKind.SEMANTIC.value:
        return semantic.update_item(store_key, memory_id, updater)
    if kind == MemoryKind.PROFILE.value:
        return profile.update_item(store_key, memory_id, updater)
    return None


def get_item_by_id(
    *,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    memory_id: str,
) -> MemoryItem | None:
    parsed = _parse_memory_id(memory_id)
    if parsed is None:
        return None
    store_key, kind = parsed
    if kind == MemoryKind.SHORT_TERM.value:
        return short_term.get_item(store_key, memory_id)
    if kind == MemoryKind.SEMANTIC.value:
        return semantic.get_item(store_key, memory_id)
    if kind == MemoryKind.PROFILE.value:
        return profile.get_item(store_key, memory_id)
    return None


def _parse_memory_id(memory_id: str) -> tuple[str, str] | None:
    if not isinstance(memory_id, str):
        return None
    parts = memory_id.split(":")
    if len(parts) < 3:
        return None
    store_key = ":".join(parts[:-2])
    kind = parts[-2]
    return store_key, kind


def _normalize_links(value: object) -> list[LinkRecord]:
    if not isinstance(value, list):
        return []
    output: list[LinkRecord] = []
    for entry in value:
        if isinstance(entry, dict):
            output.append(dict(entry))
    return output


def _link_exists(existing: list[LinkRecord], link: LinkRecord) -> bool:
    for entry in existing:
        if entry.get("type") == link.get("type") and entry.get("to_id") == link.get("to_id"):
            return True
    return False


def _apply_link_limit(
    links: list[LinkRecord],
    previews: object,
    *,
    max_links: int,
) -> tuple[list[LinkRecord], dict[str, str]]:
    preview_map = previews if isinstance(previews, dict) else {}
    trimmed = list(links)
    if max_links > 0 and len(trimmed) > max_links:
        excess = len(trimmed) - max_links
        trimmed = trimmed[excess:]
    trimmed_ids = {entry.get("to_id") for entry in trimmed}
    next_preview: dict[str, str] = {}
    for key, value in preview_map.items():
        if key in trimmed_ids and isinstance(value, str):
            next_preview[key] = value
    return trimmed, next_preview


__all__ = [
    "LinkTracker",
    "add_link_to_item",
    "build_link_record",
    "build_preview_for_item",
    "build_preview_for_tool",
    "get_item_by_id",
    "update_item_by_id",
]
