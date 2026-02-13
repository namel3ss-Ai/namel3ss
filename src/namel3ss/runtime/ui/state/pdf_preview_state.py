from __future__ import annotations

from namel3ss.rag.determinism.json_policy import stable_preview_query
from namel3ss.rag.retrieval.pdf_preview_mapper import build_preview_page_url, citation_color_index


PDF_PREVIEW_STATE_SCHEMA_VERSION = "ui.pdf_preview_state@1"
_ALLOWED_HIGHLIGHT_MODES = {"anchor", "bbox", "span", "token_positions", "unavailable"}


def ensure_pdf_preview_state(chat: dict) -> dict[str, object]:
    normalized = normalize_pdf_preview_state(chat.get("pdf_preview_state"))
    chat["pdf_preview_state"] = normalized
    return normalized


def normalize_pdf_preview_state(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    highlight_mode = _text(data.get("highlight_mode"))
    if highlight_mode not in _ALLOWED_HIGHLIGHT_MODES:
        highlight_mode = "unavailable"
    return {
        "active": bool(data.get("active")),
        "chunk_id": _text(data.get("chunk_id")),
        "citation_id": _text(data.get("citation_id")),
        "color_index": _color_index(data.get("color_index")),
        "deep_link_query": _text(data.get("deep_link_query")),
        "doc_id": _text(data.get("doc_id") or data.get("document_id")),
        "highlight_mode": highlight_mode,
        "page_number": _positive(data.get("page_number") or data.get("page"), default=1),
        "preview_url": _text(data.get("preview_url")),
        "schema_version": _text(data.get("schema_version")) or PDF_PREVIEW_STATE_SCHEMA_VERSION,
    }


def apply_pdf_preview_citation_state(chat: dict, citation: dict[str, object]) -> dict[str, object]:
    citation_id = _text(citation.get("citation_id"))
    doc_id = _text(citation.get("doc_id") or citation.get("document_id"))
    page_number = _positive(citation.get("page_number"), default=1)
    chunk_id = _text(citation.get("chunk_id"))
    preview_target = citation.get("preview_target") if isinstance(citation.get("preview_target"), dict) else {}
    highlight_mode = _highlight_mode(preview_target)
    deep_link_query = _extension_text(citation, key="deep_link_query") or stable_preview_query(
        doc_id=doc_id,
        page_number=page_number,
        citation_id=citation_id,
    )
    preview_url = build_preview_page_url(
        document_id=doc_id,
        page_number=page_number,
        chunk_id=chunk_id,
        citation_id=citation_id,
    )
    payload = {
        "active": bool(doc_id and chunk_id and citation_id),
        "chunk_id": chunk_id,
        "citation_id": citation_id,
        "color_index": citation_color_index(citation_id),
        "deep_link_query": deep_link_query,
        "doc_id": doc_id,
        "highlight_mode": highlight_mode,
        "page_number": page_number,
        "preview_url": preview_url,
        "schema_version": PDF_PREVIEW_STATE_SCHEMA_VERSION,
    }
    chat["pdf_preview_state"] = payload
    return payload


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


def _extension_text(citation: dict[str, object], *, key: str) -> str:
    extensions = citation.get("extensions")
    if not isinstance(extensions, dict):
        return ""
    return _text(extensions.get(key))


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


def _color_index(value: object) -> int:
    parsed = _non_negative(value, default=0)
    return parsed % 8


__all__ = [
    "PDF_PREVIEW_STATE_SCHEMA_VERSION",
    "apply_pdf_preview_citation_state",
    "ensure_pdf_preview_state",
    "normalize_pdf_preview_state",
]
