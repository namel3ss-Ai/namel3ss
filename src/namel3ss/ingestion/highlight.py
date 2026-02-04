from __future__ import annotations

from namel3ss.ingestion.chunk import chunk_pages_with_spans


HIGHLIGHT_STATUS_EXACT = "exact"
HIGHLIGHT_STATUS_UNAVAILABLE = "unavailable"


def attach_highlight_anchors(
    pages: list[str],
    chunks: list[dict],
    *,
    document_id: str,
    max_chars: int,
    overlap: int,
) -> list[dict]:
    expected = chunk_pages_with_spans(pages, max_chars=max_chars, overlap=overlap)
    expected_map = {entry.get("chunk_index"): entry for entry in expected if isinstance(entry, dict)}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        anchor = _highlight_anchor(chunk, expected_map.get(chunk.get("chunk_index")), document_id=document_id)
        chunk["highlight"] = anchor
    return chunks


def _highlight_anchor(chunk: dict, expected: dict | None, *, document_id: str) -> dict:
    page_number = _coerce_int(chunk.get("page_number"))
    chunk_index = _coerce_int(chunk.get("chunk_index"))
    chunk_id = f"{document_id}:{chunk_index}" if chunk_index is not None else str(chunk.get("chunk_id") or "")
    if (
        expected
        and page_number is not None
        and chunk_index is not None
        and expected.get("page_number") == page_number
        and expected.get("chunk_index") == chunk_index
        and expected.get("text") == chunk.get("text")
    ):
        start_char = _coerce_int(expected.get("start_char"))
        end_char = _coerce_int(expected.get("end_char"))
        if start_char is not None and end_char is not None and start_char >= 0 and end_char > start_char:
            return {
                "document_id": document_id,
                "page_number": page_number,
                "chunk_id": chunk_id,
                "start_char": start_char,
                "end_char": end_char,
                "status": HIGHLIGHT_STATUS_EXACT,
            }
    return {
        "document_id": document_id,
        "page_number": page_number if page_number is not None else 0,
        "chunk_id": chunk_id,
        "start_char": None,
        "end_char": None,
        "status": HIGHLIGHT_STATUS_UNAVAILABLE,
    }


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


__all__ = ["attach_highlight_anchors", "HIGHLIGHT_STATUS_EXACT", "HIGHLIGHT_STATUS_UNAVAILABLE"]
