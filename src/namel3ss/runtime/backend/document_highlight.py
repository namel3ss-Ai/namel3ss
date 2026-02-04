from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def highlights_from_state(
    state: dict,
    document_id: str,
    page_number: int,
    chunk_id: str | None,
    page_text: str,
) -> list[dict]:
    entries = _index_entries(state)
    highlights: list[dict] = []
    for entry in entries:
        if entry.get("document_id") != document_id:
            continue
        if entry.get("page_number") != page_number:
            continue
        entry_chunk_id = entry.get("chunk_id")
        if chunk_id and entry_chunk_id != chunk_id:
            continue
        highlight = _normalize_highlight(entry, document_id=document_id, page_number=page_number)
        highlight = _validate_highlight_span(highlight, page_text)
        highlights.append(highlight)
    if chunk_id and not highlights:
        highlights.append(_unavailable_highlight(document_id, page_number, chunk_id))
    highlights.sort(key=_highlight_sort_key)
    return highlights


def fallback_highlights(document_id: str, page_number: int, chunk_id: str | None) -> list[dict]:
    if chunk_id:
        return [_unavailable_highlight(document_id, page_number, chunk_id)]
    return []


def _index_entries(state: dict) -> list[dict]:
    if not isinstance(state, dict):
        return []
    index = state.get("index")
    if not isinstance(index, dict):
        return []
    entries = index.get("chunks")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _normalize_highlight(entry: dict, *, document_id: str, page_number: int) -> dict:
    entry_chunk_id = entry.get("chunk_id")
    chunk_id = entry_chunk_id if isinstance(entry_chunk_id, str) else f"{document_id}:{entry.get('chunk_index')}"
    highlight = entry.get("highlight")
    if not isinstance(highlight, dict):
        return _unavailable_highlight(document_id, page_number, chunk_id)
    status = highlight.get("status")
    if not isinstance(status, str):
        return _unavailable_highlight(document_id, page_number, chunk_id)
    status_value = status.strip().lower()
    if status_value not in {"exact", "unavailable"}:
        raise Namel3ssError(_highlight_status_message(status_value))
    if _string_value(highlight.get("document_id")) and highlight.get("document_id") != document_id:
        raise Namel3ssError(_highlight_identity_message())
    if _coerce_int(highlight.get("page_number")) and highlight.get("page_number") != page_number:
        raise Namel3ssError(_highlight_identity_message())
    if _string_value(highlight.get("chunk_id")) and highlight.get("chunk_id") != chunk_id:
        raise Namel3ssError(_highlight_identity_message())
    if status_value != "exact":
        return _unavailable_highlight(document_id, page_number, chunk_id)
    start_char = _coerce_int(highlight.get("start_char"))
    end_char = _coerce_int(highlight.get("end_char"))
    if start_char is None or end_char is None or start_char < 0 or end_char <= start_char:
        raise Namel3ssError(_highlight_span_message())
    return {
        "document_id": document_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "start_char": start_char,
        "end_char": end_char,
        "status": "exact",
    }


def _validate_highlight_span(anchor: dict, page_text: str) -> dict:
    if anchor.get("status") != "exact":
        return anchor
    start_char = _coerce_int(anchor.get("start_char"))
    end_char = _coerce_int(anchor.get("end_char"))
    if start_char is None or end_char is None:
        raise Namel3ssError(_highlight_span_message())
    if end_char > len(page_text):
        raise Namel3ssError(_highlight_span_range_message())
    return anchor


def _highlight_sort_key(anchor: dict) -> tuple[int, int, str]:
    status = anchor.get("status")
    status_rank = 0 if status == "exact" else 1
    start_char = _coerce_int(anchor.get("start_char")) or 0
    chunk_id = anchor.get("chunk_id") if isinstance(anchor.get("chunk_id"), str) else ""
    return (status_rank, start_char, chunk_id)


def _unavailable_highlight(document_id: str, page_number: int, chunk_id: str) -> dict:
    return {
        "document_id": document_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "start_char": None,
        "end_char": None,
        "status": "unavailable",
    }


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _highlight_status_message(value: str) -> str:
    return build_guidance_message(
        what=f"Highlight status '{value}' is invalid.",
        why="Highlight status must be exact or unavailable.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )


def _highlight_identity_message() -> str:
    return build_guidance_message(
        what="Highlight anchor does not match chunk metadata.",
        why="Highlights must reference the same document, page, and chunk.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"chunk_id":"<checksum>:0"}',
    )


def _highlight_span_message() -> str:
    return build_guidance_message(
        what="Highlight span is invalid.",
        why="Exact highlights require valid start and end character offsets.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )


def _highlight_span_range_message() -> str:
    return build_guidance_message(
        what="Highlight span is out of range.",
        why="Highlight offsets must fit within the page text.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )


__all__ = ["fallback_highlights", "highlights_from_state"]
