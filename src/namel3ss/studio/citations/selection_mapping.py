from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.citations.citation_schema import CITATION_INVARIANT_ERROR_CODE


def map_citation_selection(citation: Mapping[str, object]) -> dict[str, object]:
    document_id = _text(citation.get("document_id"))
    page_number = _as_positive_int(citation.get("page_number"))
    chunk_id = _text(citation.get("chunk_id"))
    source_id = _text(citation.get("source_id"))

    if not document_id and source_id:
        document_id = _parse_source_id(source_id)[0]
    if page_number <= 0 and source_id:
        page_number = _parse_source_id(source_id)[1]
    if not document_id or page_number <= 0:
        raise ValueError(f"{CITATION_INVARIANT_ERROR_CODE}: citation selection requires document_id and page_number.")

    query = f"chunk_id={chunk_id}" if chunk_id else f"source_id={source_id}" if source_id else ""
    suffix = f"?{query}" if query else ""
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "page_number": page_number,
        "preview_url": f"/api/documents/{document_id}/pages/{page_number}{suffix}",
        "source_id": source_id,
    }


def _parse_source_id(value: str) -> tuple[str, int]:
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if len(parts) < 2:
        return "", 0
    page_candidate = parts[-2]
    if not page_candidate.isdigit():
        return "", 0
    document_id = ":".join(parts[:-2]) if len(parts) > 2 else parts[0]
    return document_id, int(page_candidate)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_positive_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed > 0 else 0
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else 0
    return 0


__all__ = ["map_citation_selection"]
