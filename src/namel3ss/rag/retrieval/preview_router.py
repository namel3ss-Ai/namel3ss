from __future__ import annotations

from urllib.parse import quote, urlencode

from namel3ss.rag.determinism.json_policy import stable_preview_query


BASIC_PREVIEW_SCHEMA_VERSION = "rag.preview_basic@1"


def build_preview_routes(
    *,
    citations: list[dict[str, object]],
    snippet_by_chunk: dict[str, str] | None = None,
    schema_version: str = BASIC_PREVIEW_SCHEMA_VERSION,
) -> list[dict[str, object]]:
    snippets = snippet_by_chunk if isinstance(snippet_by_chunk, dict) else {}
    rows: list[dict[str, object]] = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        citation_id = _text(citation.get("citation_id"))
        doc_id = _text(citation.get("doc_id") or citation.get("document_id"))
        page_number = _positive(citation.get("page_number"), default=1)
        chunk_id = _text(citation.get("chunk_id"))
        if not citation_id or not doc_id or not chunk_id:
            continue
        snippet = _snippet(snippets.get(chunk_id, citation.get("snippet")))
        rows.append(
            {
                "schema_version": schema_version.strip() or BASIC_PREVIEW_SCHEMA_VERSION,
                "citation_id": citation_id,
                "document_id": doc_id,
                "page_number": page_number,
                "chunk_id": chunk_id,
                "preview_url": _preview_url(doc_id=doc_id, page_number=page_number, chunk_id=chunk_id),
                "deep_link_query": stable_preview_query(
                    doc_id=doc_id,
                    page_number=page_number,
                    citation_id=citation_id,
                ),
                "snippet": snippet,
            }
        )
    rows.sort(
        key=lambda row: (
            _positive(row.get("page_number"), default=1),
            _text(row.get("document_id")),
            _text(row.get("chunk_id")),
            _text(row.get("citation_id")),
        )
    )
    return rows


def _preview_url(*, doc_id: str, page_number: int, chunk_id: str) -> str:
    params = urlencode([("chunk_id", chunk_id)])
    return f"/api/documents/{quote(doc_id, safe='')}/pages/{page_number}?{params}"


def _snippet(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if len(text) <= 320:
        return text
    return f"{text[:320]}..."


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _positive(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) > 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed > 0:
            return parsed
    return default


__all__ = [
    "BASIC_PREVIEW_SCHEMA_VERSION",
    "build_preview_routes",
]
