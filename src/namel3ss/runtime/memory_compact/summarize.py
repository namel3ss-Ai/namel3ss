from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_links.model import link_sort_key
from namel3ss.runtime.memory_links.preview import preview_text


MAX_SUMMARY_SEGMENTS = 6
MAX_SEGMENT_LEN = 80
MAX_SUMMARY_LEN = 240


@dataclass(frozen=True)
class CompactionSummary:
    text: str
    lines: list[str]
    ledger: list[dict]


def summarize_items(items: list[MemoryItem]) -> CompactionSummary:
    ordered = sorted(items, key=lambda entry: (entry.created_at, entry.id))
    summary_text = _summary_text(ordered)
    lines = _summary_lines(ordered)
    ledger = _summary_ledger(ordered)
    return CompactionSummary(text=summary_text, lines=lines, ledger=ledger)


def _summary_text(items: list[MemoryItem]) -> str:
    segments: list[str] = []
    for item in items[:MAX_SUMMARY_SEGMENTS]:
        snippet = preview_text(item.text, max_length=MAX_SEGMENT_LEN)
        if not snippet:
            continue
        segments.append(f"{item.source}: {snippet}")
    summary = " | ".join(segments)
    if not summary:
        summary = "Summary of compacted items."
    if len(summary) > MAX_SUMMARY_LEN:
        summary = summary[:MAX_SUMMARY_LEN].rstrip() + "..."
    return summary


def _summary_lines(items: list[MemoryItem]) -> list[str]:
    count = len(items)
    lines = ["Compaction summary created.", f"Items compacted are {count}."]
    for item in items[:MAX_SUMMARY_SEGMENTS]:
        snippet = preview_text(item.text, max_length=MAX_SEGMENT_LEN)
        if not snippet:
            continue
        lines.append(_line_with_preview(f"Item from {item.source} is", snippet))
    return lines


def _summary_ledger(items: list[MemoryItem]) -> list[dict]:
    ledger: list[dict] = []
    for item in items:
        meta = item.meta or {}
        entry = {
            "memory_id": item.id,
            "kind": item.kind.value,
            "phase_id": meta.get("phase_id") or "phase-unknown",
            "space": meta.get("space") or "unknown",
            "owner": meta.get("owner") or "unknown",
            "lane": meta.get("lane") or "unknown",
            "preview": preview_text(item.text, max_length=MAX_SEGMENT_LEN),
            "links": _links_for_item(item),
            "link_preview_text": _preview_map(item),
        }
        ledger.append(entry)
    return ledger


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


def _line_with_preview(prefix: str, preview: str) -> str:
    cleaned = preview.strip()
    if cleaned.endswith((".", "!", "?", ";", ":")):
        return f"{prefix} {cleaned}"
    return f"{prefix} {cleaned}."


__all__ = [
    "CompactionSummary",
    "MAX_SEGMENT_LEN",
    "MAX_SUMMARY_LEN",
    "MAX_SUMMARY_SEGMENTS",
    "summarize_items",
]
