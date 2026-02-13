from __future__ import annotations

from namel3ss.ingestion.normalize import preview_text
from namel3ss.ingestion.store import store_report, update_index


INDEX_SCHEMA_VERSION = "rag.index@1"


def index_document_chunks(
    *,
    state: dict,
    document: dict[str, object],
    chunk_rows: list[dict[str, object]],
    parser_payload: dict[str, object] | None = None,
    status: str = "pass",
    schema_version: str = INDEX_SCHEMA_VERSION,
) -> dict[str, object]:
    doc_id = _text(document.get("doc_id"))
    source_name = _source_name(document, chunk_rows)
    status_value = _status(status)
    parser_map = parser_payload if isinstance(parser_payload, dict) else {}
    report = _build_report(
        doc_id=doc_id,
        source_name=source_name,
        parser_payload=parser_map,
        chunk_rows=chunk_rows,
        status=status_value,
    )
    store_report(state, upload_id=doc_id, report=report)
    update_index(
        state,
        upload_id=doc_id,
        chunks=[_index_chunk_entry(row, doc_id=doc_id, source_name=source_name) for row in chunk_rows],
        low_quality=status_value == "warn",
    )
    return {
        "schema_version": schema_version.strip() or INDEX_SCHEMA_VERSION,
        "document_id": doc_id,
        "chunk_count": len(chunk_rows),
        "status": status_value,
    }


def _index_chunk_entry(row: dict[str, object], *, doc_id: str, source_name: str) -> dict[str, object]:
    return {
        "document_id": _text(row.get("doc_id")) or doc_id,
        "source_name": _text(row.get("source_name")) or source_name,
        "page_number": _positive(row.get("page_number"), default=1),
        "chunk_index": _non_negative(row.get("chunk_index"), default=0),
        "ingestion_phase": _phase(row.get("ingestion_phase")),
        "keywords": _keywords(row.get("keywords")),
        "text": _text(row.get("text")),
        "chars": _non_negative(row.get("chars"), default=0),
        "highlight": _highlight(row.get("highlight")),
    }


def _build_report(
    *,
    doc_id: str,
    source_name: str,
    parser_payload: dict[str, object],
    chunk_rows: list[dict[str, object]],
    status: str,
) -> dict[str, object]:
    detected = parser_payload.get("detected") if isinstance(parser_payload.get("detected"), dict) else {}
    pages = parser_payload.get("pages") if isinstance(parser_payload.get("pages"), list) else []
    preview_source = " ".join(_text(row.get("text")) for row in chunk_rows[:3])
    method_used = _text(parser_payload.get("method_used")) or "primary"
    report: dict[str, object] = {
        "upload_id": doc_id,
        "status": status,
        "method_used": method_used,
        "detected": detected,
        "signals": {},
        "reasons": [],
        "preview": preview_text(preview_source, limit=240),
        "provenance": {
            "document_id": doc_id,
            "source_name": source_name,
        },
        "page_text": [str(page) for page in pages if isinstance(page, str)],
    }
    if parser_payload.get("fallback_used") is True:
        report["fallback_used"] = method_used
    return report


def _keywords(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    rows: list[str] = []
    for item in value:
        token = _text(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _highlight(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {
            "document_id": "",
            "page_number": 0,
            "chunk_id": "",
            "start_char": None,
            "end_char": None,
            "status": "unavailable",
        }
    status = _text(value.get("status")).lower()
    if status == "exact":
        start_char = _non_negative(value.get("start_char"), default=-1)
        end_char = _non_negative(value.get("end_char"), default=-1)
        if start_char >= 0 and end_char > start_char:
            return {
                "document_id": _text(value.get("document_id")),
                "page_number": _positive(value.get("page_number"), default=1),
                "chunk_id": _text(value.get("chunk_id")),
                "start_char": start_char,
                "end_char": end_char,
                "status": "exact",
            }
    return {
        "document_id": _text(value.get("document_id")),
        "page_number": _positive(value.get("page_number"), default=1),
        "chunk_id": _text(value.get("chunk_id")),
        "start_char": None,
        "end_char": None,
        "status": "unavailable",
    }


def _source_name(document: dict[str, object], rows: list[dict[str, object]]) -> str:
    if rows:
        text = _text(rows[0].get("source_name"))
        if text:
            return text
    title = _text(document.get("title"))
    if title:
        return title
    return _text(document.get("doc_id"))


def _status(value: object) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"pass", "warn", "block"}:
            return lowered
    return "pass"


def _phase(value: object) -> str:
    if isinstance(value, str) and value.strip().lower() == "quick":
        return "quick"
    return "deep"


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
    "INDEX_SCHEMA_VERSION",
    "index_document_chunks",
]
