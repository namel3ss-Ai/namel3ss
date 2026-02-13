from __future__ import annotations

from urllib.parse import quote, urlencode

from namel3ss.rag.determinism.text_normalizer import build_boundary_signature, canonical_text


CHUNK_INSPECTION_SCHEMA_VERSION = "rag.chunk_inspection@1"
DEFAULT_LIMIT = 200


def build_chunk_inspection_payload(
    *,
    state: dict,
    document_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    schema_version: str = CHUNK_INSPECTION_SCHEMA_VERSION,
) -> dict[str, object]:
    document_filter = _text(document_id)
    normalized_limit = _limit_value(limit)
    normalized_offset = _offset_value(offset)
    chunks = _index_chunks(state)
    reports = _ingestion_reports(state)
    documents = _document_summaries(chunks, reports)
    rows = _chunk_rows(chunks, document_filter=document_filter)
    total_count = len(rows)
    rows = rows[normalized_offset:]
    if normalized_limit is not None:
        rows = rows[:normalized_limit]
    pages = _parsed_pages(reports, document_id=document_filter)
    return {
        "schema_version": _text(schema_version) or CHUNK_INSPECTION_SCHEMA_VERSION,
        "document_id": document_filter,
        "documents": documents,
        "limit": normalized_limit if normalized_limit is not None else 0,
        "offset": normalized_offset,
        "pages": pages,
        "rows": rows,
        "total_count": total_count,
    }


def _document_summaries(chunks: list[dict[str, object]], reports: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for chunk in chunks:
        doc_id = _doc_id(chunk)
        source_name = _text(chunk.get("source_name")) or doc_id
        page_number = _positive_int(chunk.get("page_number"), default=1)
        if doc_id not in grouped:
            grouped[doc_id] = {
                "doc_id": doc_id,
                "page_count": 0,
                "source_name": source_name,
                "_pages_seen": set(),
                "_chunk_count": 0,
            }
        entry = grouped[doc_id]
        entry["_chunk_count"] = int(entry["_chunk_count"]) + 1
        pages_seen = entry["_pages_seen"]
        if isinstance(pages_seen, set):
            pages_seen.add(page_number)
    rows: list[dict[str, object]] = []
    for doc_id in sorted(grouped.keys()):
        entry = grouped[doc_id]
        report = reports.get(doc_id, {})
        report_pages = report.get("page_text")
        page_count = 0
        if isinstance(report_pages, list):
            page_count = len(report_pages)
        elif isinstance(entry.get("_pages_seen"), set):
            page_count = len(entry["_pages_seen"])
        rows.append(
            {
                "chunk_count": int(entry.get("_chunk_count") or 0),
                "doc_id": doc_id,
                "page_count": page_count,
                "source_name": _text(entry.get("source_name")) or doc_id,
            }
        )
    return rows


def _chunk_rows(chunks: list[dict[str, object]], *, document_filter: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for chunk in chunks:
        doc_id = _doc_id(chunk)
        if document_filter and doc_id != document_filter:
            continue
        page_number = _positive_int(chunk.get("page_number"), default=1)
        chunk_index = _non_negative_int(chunk.get("chunk_index"), default=0)
        chunk_id = _text(chunk.get("chunk_id")) or f"{doc_id}:{chunk_index}"
        text = canonical_text(chunk.get("text"))
        boundary_signature = _boundary_signature(
            chunk=chunk,
            doc_id=doc_id,
            page_number=page_number,
            chunk_index=chunk_index,
            text=text,
        )
        rows.append(
            {
                "boundary_signature": boundary_signature,
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "deep_link_query": _stable_chunk_query(
                    doc_id=doc_id,
                    page_number=page_number,
                    chunk_id=chunk_id,
                ),
                "doc_id": doc_id,
                "ingestion_phase": _phase(chunk.get("ingestion_phase")),
                "page_number": page_number,
                "preview_url": _preview_url(
                    doc_id=doc_id,
                    page_number=page_number,
                    chunk_id=chunk_id,
                ),
                "snippet": _snippet(text),
                "source_name": _text(chunk.get("source_name")) or doc_id,
            }
        )
    rows.sort(
        key=lambda row: (
            _text(row.get("doc_id")),
            _non_negative_int(row.get("chunk_index"), default=0),
            _positive_int(row.get("page_number"), default=1),
            _text(row.get("chunk_id")),
        )
    )
    return rows


def _parsed_pages(reports: dict[str, dict[str, object]], *, document_id: str) -> list[dict[str, object]]:
    if not document_id:
        return []
    report = reports.get(document_id, {})
    pages = report.get("page_text")
    if not isinstance(pages, list):
        return []
    rows: list[dict[str, object]] = []
    for index, page in enumerate(pages, start=1):
        text = canonical_text(page)
        rows.append(
            {
                "page_number": index,
                "snippet": _snippet(text),
            }
        )
    return rows


def _index_chunks(state: dict) -> list[dict[str, object]]:
    index = state.get("index")
    if not isinstance(index, dict):
        return []
    chunks = index.get("chunks")
    if not isinstance(chunks, list):
        return []
    rows: list[dict[str, object]] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            rows.append(chunk)
    return rows


def _ingestion_reports(state: dict) -> dict[str, dict[str, object]]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {}
    rows: dict[str, dict[str, object]] = {}
    for key in sorted(ingestion.keys(), key=str):
        value = ingestion.get(key)
        if not isinstance(value, dict):
            continue
        rows[_text(key)] = value
    return rows


def _doc_id(chunk: dict[str, object]) -> str:
    return _text(chunk.get("document_id") or chunk.get("upload_id"))


def _boundary_signature(
    *,
    chunk: dict[str, object],
    doc_id: str,
    page_number: int,
    chunk_index: int,
    text: str,
) -> str:
    provided = _text(chunk.get("boundary_signature"))
    if provided:
        return provided
    return build_boundary_signature(
        doc_id=doc_id,
        page_number=page_number,
        chunk_index=chunk_index,
        text=text,
    )


def _phase(value: object) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"quick", "deep"}:
            return lowered
    return "deep"


def _preview_url(*, doc_id: str, page_number: int, chunk_id: str) -> str:
    path = f"/api/documents/{quote(doc_id, safe='')}/pages/{page_number}"
    query = urlencode([("chunk_id", chunk_id)])
    return f"{path}?{query}"


def _stable_chunk_query(*, doc_id: str, page_number: int, chunk_id: str) -> str:
    return urlencode(
        [
            ("doc", doc_id),
            ("page", str(page_number)),
            ("chunk", chunk_id),
        ]
    )


def _snippet(value: str) -> str:
    text = " ".join(value.split())
    if len(text) <= 240:
        return text
    return f"{text[:240]}..."


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _positive_int(value: object, *, default: int) -> int:
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


def _non_negative_int(value: object, *, default: int) -> int:
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


def _limit_value(value: object) -> int | None:
    if value is None:
        return None
    limit = _non_negative_int(value, default=DEFAULT_LIMIT)
    if limit <= 0:
        return None
    return limit


def _offset_value(value: object) -> int:
    return _non_negative_int(value, default=0)


__all__ = [
    "CHUNK_INSPECTION_SCHEMA_VERSION",
    "DEFAULT_LIMIT",
    "build_chunk_inspection_payload",
]
