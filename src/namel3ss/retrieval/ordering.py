from __future__ import annotations

from decimal import Decimal


def ordering_label(use_chunk_id: bool) -> str:
    if use_chunk_id:
        return "ingestion_phase, keyword_overlap, page_number, chunk_index, chunk_id"
    return "ingestion_phase, keyword_overlap, page_number, chunk_index"


def rank_key(entry: dict, order_index: int, *, tie_break_chunk_id: bool) -> tuple:
    item = (entry, order_index)
    if tie_break_chunk_id:
        return _entry_sort_key_with_chunk_id(item)
    return _entry_sort_key(item)


def select_tier(
    entries: list[tuple[dict, int]],
    tier_request: str,
    *,
    tie_break_chunk_id: bool = False,
) -> tuple[list[dict], dict]:
    available = _phase_counts(entries)
    phases = [phase for phase in ("deep", "quick") if available.get(phase)]
    ordered = order_entries(entries, tie_break_chunk_id=tie_break_chunk_id)
    selection: dict = {"available": phases, "counts": available}
    if tier_request == "quick-only":
        selection.update({"selected": "quick", "reason": "tier_requested"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "quick"], selection
    if tier_request == "deep-only":
        selection.update({"selected": "deep", "reason": "tier_requested"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "deep"], selection
    if available.get("deep") and available.get("quick"):
        selection.update({"selected": "deep_then_quick", "reason": "deep_and_quick_available"})
        return ordered, selection
    if available.get("deep"):
        selection.update({"selected": "deep", "reason": "deep_available"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "deep"], selection
    if available.get("quick"):
        selection.update({"selected": "quick", "reason": "quick_only_available"})
        return [entry for entry in ordered if entry.get("ingestion_phase") == "quick"], selection
    selection.update({"selected": "none", "reason": "no_chunks"})
    return [], selection


def order_entries(entries: list[tuple[dict, int]], *, tie_break_chunk_id: bool = False) -> list[dict]:
    key_fn = _entry_sort_key_with_chunk_id if tie_break_chunk_id else _entry_sort_key
    ordered = sorted(entries, key=key_fn)
    return [entry for entry, _ in ordered]


def _entry_sort_key(item: tuple[dict, int]) -> tuple[int, int, int, int, int]:
    entry, order = item
    phase = entry.get("ingestion_phase")
    phase_rank = 0 if phase == "deep" else 1
    overlap = int(entry.get("keyword_overlap") or 0)
    page_number = coerce_int(entry.get("page_number")) or 0
    chunk_index = coerce_int(entry.get("chunk_index")) or 0
    return (phase_rank, -overlap, page_number, chunk_index, order)


def _entry_sort_key_with_chunk_id(item: tuple[dict, int]) -> tuple[int, int, int, int, str]:
    entry, _order = item
    phase = entry.get("ingestion_phase")
    phase_rank = 0 if phase == "deep" else 1
    overlap = int(entry.get("keyword_overlap") or 0)
    page_number = coerce_int(entry.get("page_number")) or 0
    chunk_index = coerce_int(entry.get("chunk_index")) or 0
    chunk_id = str(entry.get("chunk_id") or "")
    return (phase_rank, -overlap, page_number, chunk_index, chunk_id)


def _phase_counts(entries: list[tuple[dict, int]]) -> dict:
    counts = {"deep": 0, "quick": 0}
    for entry, _ in entries:
        phase = entry.get("ingestion_phase")
        if phase in counts:
            counts[phase] += 1
    return counts


def coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
    return None


__all__ = ["coerce_int", "ordering_label", "order_entries", "rank_key", "select_tier"]
