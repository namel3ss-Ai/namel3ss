from __future__ import annotations

from namel3ss.ingestion.keywords import extract_keywords
from namel3ss.ingestion.progressive import chunk_with_phase
from namel3ss.rag.contracts.chunk_model import build_chunk_model
from namel3ss.rag.determinism.text_normalizer import canonical_text


CHUNKING_VERSION = "rag.chunking@1"
DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP = 100


def build_chunk_rows(
    *,
    document: dict[str, object],
    pages: list[str],
    source_name: str,
    phase: str = "deep",
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
    chunking_version: str = CHUNKING_VERSION,
) -> list[dict[str, object]]:
    doc_id = _text(document.get("doc_id"))
    source_name_value = _text(source_name) or doc_id
    phase_value = _phase(phase)
    normalized_pages = [canonical_text(page) for page in pages if isinstance(page, str)]
    if not normalized_pages:
        normalized_pages = [""]
    raw_chunks = chunk_with_phase(
        normalized_pages,
        document_id=doc_id,
        source_name=source_name_value,
        phase=phase_value,
        max_chars=_positive(max_chars, default=DEFAULT_MAX_CHARS),
        overlap=_non_negative(overlap, default=DEFAULT_OVERLAP),
        include_highlights=True,
    )
    rows: list[dict[str, object]] = []
    for raw in raw_chunks:
        page_number = _positive(raw.get("page_number"), default=1)
        chunk_index = _non_negative(raw.get("chunk_index"), default=0)
        text = canonical_text(raw.get("text"))
        highlight = _highlight_payload(
            raw.get("highlight"),
            doc_id=doc_id,
            page_number=page_number,
            chunk_index=chunk_index,
        )
        span = _highlight_span(highlight)
        model = build_chunk_model(
            doc_id=doc_id,
            page_number=page_number,
            chunk_index=chunk_index,
            text=text,
            span=span,
            anchor=text,
            schema_version=chunking_version.strip() or CHUNKING_VERSION,
        )
        row = dict(model)
        row["chars"] = len(text)
        row["highlight"] = highlight
        row["ingestion_phase"] = phase_value
        row["keywords"] = extract_keywords(text)
        row["source_name"] = source_name_value
        rows.append(row)
    rows.sort(key=lambda entry: (_positive(entry.get("page_number"), default=1), _non_negative(entry.get("chunk_index"), default=0)))
    return rows


def _highlight_payload(value: object, *, doc_id: str, page_number: int, chunk_index: int) -> dict[str, object]:
    chunk_id = f"{doc_id}:{chunk_index}"
    if isinstance(value, dict):
        status = _text(value.get("status")).lower()
        if status == "exact":
            start_char = _non_negative(value.get("start_char"), default=-1)
            end_char = _non_negative(value.get("end_char"), default=-1)
            if start_char >= 0 and end_char > start_char:
                return {
                    "document_id": doc_id,
                    "page_number": page_number,
                    "chunk_id": chunk_id,
                    "start_char": start_char,
                    "end_char": end_char,
                    "status": "exact",
                }
    return {
        "document_id": doc_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "start_char": None,
        "end_char": None,
        "status": "unavailable",
    }


def _highlight_span(value: dict[str, object]) -> dict[str, int] | None:
    if value.get("status") != "exact":
        return None
    start_char = _non_negative(value.get("start_char"), default=-1)
    end_char = _non_negative(value.get("end_char"), default=-1)
    if start_char < 0 or end_char <= start_char:
        return None
    return {
        "start_char": start_char,
        "end_char": end_char,
    }


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _phase(value: object) -> str:
    if not isinstance(value, str):
        return "deep"
    lowered = value.strip().lower()
    if lowered == "quick":
        return "quick"
    return "deep"


def _positive(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) > 0:
        return int(value)
    return default


def _non_negative(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) >= 0:
        return int(value)
    return default


__all__ = [
    "CHUNKING_VERSION",
    "DEFAULT_MAX_CHARS",
    "DEFAULT_OVERLAP",
    "build_chunk_rows",
]
