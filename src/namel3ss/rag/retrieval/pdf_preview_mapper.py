from __future__ import annotations

import hashlib
from urllib.parse import quote, urlencode

from namel3ss.rag.determinism.json_policy import stable_preview_query


PDF_PREVIEW_SCHEMA_VERSION = "rag.preview_pdf@1"
DEFAULT_COLOR_PALETTE_SIZE = 8


def build_pdf_preview_routes(
    *,
    citations: list[dict[str, object]],
    snippet_by_chunk: dict[str, str] | None = None,
    schema_version: str = PDF_PREVIEW_SCHEMA_VERSION,
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
        preview_target = citation.get("preview_target") if isinstance(citation.get("preview_target"), dict) else {}
        highlight_mode = _highlight_mode(preview_target)
        snippet = _snippet(snippets.get(chunk_id, _extension_text(citation, key="snippet")))
        deep_link_query = stable_preview_query(
            doc_id=doc_id,
            page_number=page_number,
            citation_id=citation_id,
        )
        rows.append(
            {
                "schema_version": schema_version.strip() or PDF_PREVIEW_SCHEMA_VERSION,
                "citation_id": citation_id,
                "color_index": citation_color_index(citation_id, palette_size=DEFAULT_COLOR_PALETTE_SIZE),
                "deep_link_query": deep_link_query,
                "document_id": doc_id,
                "highlight_mode": highlight_mode,
                "page_number": page_number,
                "preview_target": dict(preview_target),
                "preview_url": build_preview_page_url(
                    document_id=doc_id,
                    page_number=page_number,
                    chunk_id=chunk_id,
                    citation_id=citation_id,
                ),
                "chunk_id": chunk_id,
                "snippet": snippet,
            }
        )
    rows.sort(key=_sort_key)
    return rows


def build_preview_page_url(*, document_id: str, page_number: int, chunk_id: str, citation_id: str) -> str:
    params = urlencode(
        [
            ("chunk_id", chunk_id),
            ("citation_id", citation_id),
        ]
    )
    return f"/api/documents/{quote(document_id, safe='')}/pages/{max(1, int(page_number))}?{params}"


def citation_color_index(citation_id: str, *, palette_size: int = DEFAULT_COLOR_PALETTE_SIZE) -> int:
    text = _text(citation_id)
    size = max(1, int(palette_size or DEFAULT_COLOR_PALETTE_SIZE))
    if not text:
        return 0
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def _highlight_mode(preview_target: dict[str, object]) -> str:
    if isinstance(preview_target.get("bbox"), list) and preview_target.get("bbox"):
        return "bbox"
    span = preview_target.get("span")
    if isinstance(span, dict):
        start_char = _non_negative(span.get("start_char"), default=-1)
        end_char = _non_negative(span.get("end_char"), default=-1)
        if start_char >= 0 and end_char > start_char:
            return "span"
    if isinstance(preview_target.get("token_positions"), list) and preview_target.get("token_positions"):
        return "token_positions"
    if _text(preview_target.get("anchor")):
        return "anchor"
    return "unavailable"


def _sort_key(row: dict[str, object]) -> tuple[int, str, str, str]:
    return (
        _positive(row.get("page_number"), default=1),
        _text(row.get("document_id")),
        _text(row.get("chunk_id")),
        _text(row.get("citation_id")),
    )


def _extension_text(citation: dict[str, object], *, key: str) -> str:
    extensions = citation.get("extensions")
    if not isinstance(extensions, dict):
        return ""
    return _text(extensions.get(key))


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
    parsed = _non_negative(value, default=-1)
    if parsed > 0:
        return parsed
    return default


def _non_negative(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed >= 0:
            return parsed
    return default


__all__ = [
    "DEFAULT_COLOR_PALETTE_SIZE",
    "PDF_PREVIEW_SCHEMA_VERSION",
    "build_pdf_preview_routes",
    "build_preview_page_url",
    "citation_color_index",
]
