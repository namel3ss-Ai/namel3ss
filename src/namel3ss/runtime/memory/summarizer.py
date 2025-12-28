from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem


def summarize_items(
    items: list[MemoryItem],
    *,
    prior_summary: str | None = None,
    max_items: int = 6,
    max_segment_len: int = 80,
    max_summary_len: int = 240,
) -> str:
    segments: list[str] = []
    if prior_summary:
        segments.append(f"Earlier: {_trim(prior_summary, max_segment_len)}")
    for item in items[:max_items]:
        snippet = _trim(_normalize_text(item.text), max_segment_len)
        segments.append(f"{item.source}: {snippet}")
    summary = " | ".join(segments)
    if len(summary) > max_summary_len:
        summary = summary[:max_summary_len].rstrip() + "..."
    return summary


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def _trim(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


__all__ = ["summarize_items"]
