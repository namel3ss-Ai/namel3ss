from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem


def _phase_id_for_item(item: MemoryItem, fallback: str) -> str:
    meta = item.meta or {}
    phase_id = meta.get("phase_id")
    if isinstance(phase_id, str) and phase_id:
        return phase_id
    return fallback


def _meta_value(item: MemoryItem | None, key: str, fallback: str) -> str:
    if not item:
        return fallback
    meta = item.meta or {}
    value = meta.get(key)
    if isinstance(value, str) and value:
        return value
    return fallback
