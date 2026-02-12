from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.runtime.citations.citation_schema import (
    CITATION_INVARIANT_ERROR_CODE,
    CITATION_SCHEMA_VERSION,
    CitationPayload,
)
from namel3ss.runtime.ingest.chunking.chunk_id import stable_source_id


class CitationInvariantError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = CITATION_INVARIANT_ERROR_CODE


def normalize_citations(citations: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows: list[CitationPayload] = []
    for item in citations:
        rows.append(_normalize_single(item))
    rows.sort(key=_sort_key)
    return {
        "citations": [row.to_dict() for row in rows],
        "schema_version": CITATION_SCHEMA_VERSION,
    }


def _normalize_single(value: Mapping[str, object]) -> CitationPayload:
    doc_id = _required_text(value.get("document_id"), field="document_id")
    page_number = _required_int(value.get("page_number"), field="page_number")
    chunk_index = _required_int(value.get("chunk_index"), field="chunk_index")
    snippet = _required_text(value.get("snippet"), field="snippet")
    title = _optional_text(value.get("title")) or f"{doc_id} p{page_number}"
    chunk_id = _optional_text(value.get("chunk_id")) or f"{doc_id}:{chunk_index}"
    source_id = _optional_text(value.get("source_id")) or stable_source_id(
        doc_id=doc_id,
        page_number=page_number,
        chunk_index=chunk_index,
    )
    score = _score_value(value.get("score"))
    return CitationPayload(
        snippet=snippet,
        title=title,
        source_id=source_id,
        document_id=doc_id,
        page_number=page_number,
        chunk_index=chunk_index,
        chunk_id=chunk_id,
        score=score,
    )


def _sort_key(value: CitationPayload) -> tuple[object, ...]:
    return (-value.score, value.source_id, value.page_number, value.chunk_index, value.snippet)


def _required_text(value: object, *, field: str) -> str:
    text = _optional_text(value)
    if not text:
        raise CitationInvariantError(f"{CITATION_INVARIANT_ERROR_CODE}: citation field '{field}' is required.")
    return text


def _required_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise CitationInvariantError(f"{CITATION_INVARIANT_ERROR_CODE}: citation field '{field}' must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise CitationInvariantError(f"{CITATION_INVARIANT_ERROR_CODE}: citation field '{field}' must be an integer.")


def _optional_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _score_value(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            number = 0.0
    else:
        number = 0.0
    if number < 0:
        number = 0.0
    if number > 1:
        number = 1.0
    return round(number, 4)


__all__ = ["CitationInvariantError", "normalize_citations"]
