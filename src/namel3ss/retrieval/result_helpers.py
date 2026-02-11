from __future__ import annotations

from namel3ss.retrieval.ordering import coerce_int


def candidate_fields(entry: dict, *, upload_id: str, keyword_overlap: int) -> dict:
    chunk_index = coerce_int(entry.get("chunk_index")) or 0
    chunk_id = entry.get("chunk_id")
    return {
        "chunk_id": str(chunk_id or f"{upload_id}:{chunk_index}"),
        "ingestion_phase": str(entry.get("ingestion_phase") or ""),
        "keyword_overlap": int(keyword_overlap),
        "page_number": coerce_int(entry.get("page_number")) or 0,
        "chunk_index": chunk_index,
    }


def normalize_tags(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return sorted(normalized)


__all__ = ["candidate_fields", "normalize_tags"]

