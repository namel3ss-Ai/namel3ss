from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.rag.retrieval.highlight_resolver import HIGHLIGHT_MODE_UNAVAILABLE, resolve_highlight_for_chunk
from namel3ss.rag.retrieval.pdf_preview_mapper import citation_color_index


def highlights_from_state(
    state: dict,
    document_id: str,
    page_number: int,
    chunk_id: str | None,
    page_text: str,
    citation_id: str | None = None,
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
        highlight = _resolve_entry_highlight(
            entry,
            document_id=document_id,
            page_number=page_number,
            page_text=page_text,
            citation_id=citation_id,
        )
        highlight = _validate_highlight_span(highlight, page_text)
        highlights.append(highlight)
    if chunk_id and not highlights:
        highlights.append(_unavailable_highlight(document_id, page_number, chunk_id, citation_id=citation_id))
    highlights.sort(key=_highlight_sort_key)
    return highlights


def fallback_highlights(
    document_id: str,
    page_number: int,
    chunk_id: str | None,
    citation_id: str | None = None,
) -> list[dict]:
    if chunk_id:
        return [_unavailable_highlight(document_id, page_number, chunk_id, citation_id=citation_id)]
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


def _resolve_entry_highlight(
    entry: dict,
    *,
    document_id: str,
    page_number: int,
    page_text: str,
    citation_id: str | None,
) -> dict:
    entry_chunk_id = entry.get("chunk_id")
    chunk_id = entry_chunk_id if isinstance(entry_chunk_id, str) else f"{document_id}:{entry.get('chunk_index')}"
    legacy_span = _legacy_highlight_span(entry, document_id=document_id, page_number=page_number, chunk_id=chunk_id)
    if legacy_span is not None and int(legacy_span.get("end_char") or 0) > len(page_text):
        raise Namel3ssError(_highlight_span_range_message())
    resolved = resolve_highlight_for_chunk(
        document_id=document_id,
        page_number=page_number,
        chunk_id=chunk_id,
        page_text=page_text,
        bbox=entry.get("bbox"),
        span=legacy_span or entry.get("span"),
        token_positions=entry.get("token_positions"),
        anchor=entry.get("anchor") or entry.get("text"),
        citation_id=citation_id,
    )
    if _text(citation_id):
        resolved["color_index"] = citation_color_index(_text(citation_id))
    return resolved


def _legacy_highlight_span(
    entry: dict,
    *,
    document_id: str,
    page_number: int,
    chunk_id: str,
) -> dict[str, int] | None:
    highlight = entry.get("highlight")
    if not isinstance(highlight, dict):
        return None
    status = highlight.get("status")
    if not isinstance(status, str):
        return None
    status_value = status.strip().lower()
    if status_value not in {"exact", "unavailable"}:
        raise Namel3ssError(_highlight_status_message(status_value))
    if _text(highlight.get("document_id")) and highlight.get("document_id") != document_id:
        raise Namel3ssError(_highlight_identity_message())
    if _coerce_int(highlight.get("page_number")) and highlight.get("page_number") != page_number:
        raise Namel3ssError(_highlight_identity_message())
    if _text(highlight.get("chunk_id")) and highlight.get("chunk_id") != chunk_id:
        raise Namel3ssError(_highlight_identity_message())
    if status_value != "exact":
        return None
    start_char = _coerce_int(highlight.get("start_char"))
    end_char = _coerce_int(highlight.get("end_char"))
    if start_char is None or end_char is None or start_char < 0 or end_char <= start_char:
        raise Namel3ssError(_highlight_span_message())
    return {
        "start_char": start_char,
        "end_char": end_char,
    }


def _validate_highlight_span(anchor: dict, page_text: str) -> dict:
    if anchor.get("status") != "exact":
        return anchor
    start_char = _coerce_int(anchor.get("start_char"))
    end_char = _coerce_int(anchor.get("end_char"))
    if start_char is None and end_char is None:
        return anchor
    if start_char is None or end_char is None:
        raise Namel3ssError(_highlight_span_message())
    if end_char > len(page_text):
        raise Namel3ssError(_highlight_span_range_message())
    return anchor


def _highlight_sort_key(anchor: dict) -> tuple[int, int, str, str]:
    status = anchor.get("status")
    status_rank = 0 if status == "exact" else 1
    start_char = _coerce_int(anchor.get("start_char")) or 0
    resolver = _text(anchor.get("resolver"))
    chunk_id = _text(anchor.get("chunk_id"))
    return (status_rank, start_char, resolver, chunk_id)


def _unavailable_highlight(document_id: str, page_number: int, chunk_id: str, *, citation_id: str | None) -> dict:
    payload = {
        "document_id": document_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "start_char": None,
        "end_char": None,
        "status": "unavailable",
        "resolver": HIGHLIGHT_MODE_UNAVAILABLE,
    }
    citation_text = _text(citation_id)
    if citation_text:
        payload["citation_id"] = citation_text
        payload["color_index"] = citation_color_index(citation_text)
    return payload


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


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
