from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory_links.model import LinkRecord, link_sort_key


LINK_PHRASES = {
    "depends_on": "depends on",
    "caused_by": "caused by",
    "replaced": "replaced",
    "promoted_from": "promoted from",
    "conflicts_with": "conflicts with",
    "supports": "supports",
}

PATH_PHRASES = {
    "depends_on": "This exists because it depends on another item.",
    "caused_by": "This exists because a tool result caused it.",
    "replaced": "This exists because it replaced an older item.",
    "promoted_from": "This exists because it was promoted from another space.",
    "conflicts_with": "This exists because it won a conflict.",
    "supports": "This exists because it supports another item.",
}


def link_lines(item: MemoryItem) -> list[str]:
    links = _links_for_item(item)
    if not links:
        return ["No links were recorded."]
    preview_map = _preview_map(item)
    lines: list[str] = []
    for link in links:
        phrase = LINK_PHRASES.get(link.get("type") or "", "linked to")
        preview = preview_map.get(link.get("to_id") or "")
        if preview:
            lines.append(_line_with_preview(f"Link {phrase}", preview))
        else:
            lines.append(f"Link {phrase} item.")
            target_id = link.get("to_id") or "unknown"
            lines.append(f"Target id is {target_id}.")
        reason = link.get("reason_code")
        if reason:
            lines.append(f"Reason is {reason}.")
    return lines


def path_lines(item: MemoryItem, *, max_lines: int = 6) -> list[str]:
    links = _links_for_item(item)
    if not links:
        return ["No links were found."]
    preview_map = _preview_map(item)
    lines: list[str] = []
    for link in links:
        if len(lines) >= max_lines:
            break
        phrase = PATH_PHRASES.get(link.get("type") or "", "This exists because it is linked.")
        lines.append(phrase)
        if len(lines) >= max_lines:
            break
        preview = preview_map.get(link.get("to_id") or "")
        if preview:
            lines.append(_line_with_preview("Target summary is", preview))
        else:
            target_id = link.get("to_id") or "unknown"
            lines.append(f"Target id is {target_id}.")
        if len(lines) >= max_lines:
            break
        created = link.get("created_in_phase_id")
        if created:
            lines.append(f"Link was created in phase {_format_phase_id(str(created))}.")
    return lines[:max_lines]


def _links_for_item(item: MemoryItem) -> list[LinkRecord]:
    meta = item.meta or {}
    links = meta.get("links")
    if not isinstance(links, list):
        return []
    cleaned: list[LinkRecord] = []
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


def _format_phase_id(value: str) -> str:
    if value.startswith("phase-"):
        suffix = value.split("-", 1)[1]
        if suffix.isdigit():
            return suffix
    return value


__all__ = ["link_lines", "path_lines"]
