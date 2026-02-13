from __future__ import annotations

from namel3ss.rag.contracts.citation_model import build_citation_model
from namel3ss.rag.contracts.value_norms import normalize_bbox, normalize_token_positions
from namel3ss.rag.determinism.json_policy import stable_preview_query
from namel3ss.rag.determinism.order_policy import sort_citation_rows
from namel3ss.rag.determinism.text_normalizer import normalize_anchor_text


def map_answer_citations(
    *,
    answer_text: str,
    citation_chunk_ids: list[object],
    retrieval_trace: list[object],
    index_chunks: list[object],
) -> list[dict[str, object]]:
    trace_map = _trace_map(retrieval_trace)
    chunk_map = _chunk_map(index_chunks)
    rows: list[dict[str, object]] = []
    cursor = 0
    for mention_index, chunk_id in enumerate(_chunk_ids(citation_chunk_ids)):
        trace = trace_map.get(chunk_id, {})
        chunk = chunk_map.get(chunk_id, {})
        doc_id = _text(trace.get("document_id") or trace.get("upload_id") or chunk.get("doc_id")) or _chunk_doc_id(chunk_id)
        page_number = _positive(trace.get("page_number") or chunk.get("page_number"), default=1)
        answer_span, cursor = _answer_span(str(answer_text or ""), chunk_id=chunk_id, start_at=cursor)
        citation = build_citation_model(
            doc_id=doc_id,
            page_number=page_number,
            chunk_id=chunk_id,
            answer_span=answer_span,
            preview_target=_preview_target(chunk, page_number=page_number),
            mention_index=mention_index,
        )
        citation_id = _text(citation.get("citation_id"))
        extensions = dict(citation.get("extensions") or {})
        extensions["deep_link_query"] = stable_preview_query(
            doc_id=doc_id,
            page_number=page_number,
            citation_id=citation_id,
        )
        snippet = _text(chunk.get("text"))
        if snippet:
            extensions["snippet"] = snippet[:320]
        citation["extensions"] = {key: extensions[key] for key in sorted(extensions.keys())}
        rows.append(citation)
    return sort_citation_rows(rows)


def _preview_target(chunk: dict[str, object], *, page_number: int) -> dict[str, object]:
    payload: dict[str, object] = {"page": _positive(page_number, default=1)}

    bbox = normalize_bbox(chunk.get("bbox"))
    if bbox:
        payload["bbox"] = bbox

    span = _span_from_chunk(chunk)
    if span is not None:
        payload["span"] = span

    token_positions = normalize_token_positions(chunk.get("token_positions"))
    if token_positions:
        payload["token_positions"] = token_positions

    anchor = normalize_anchor_text(chunk.get("anchor") or chunk.get("text"))
    if anchor:
        payload["anchor"] = anchor

    return payload


def _span_from_chunk(chunk: dict[str, object]) -> dict[str, int] | None:
    span = chunk.get("span")
    if isinstance(span, dict):
        start_char = _non_negative(span.get("start_char"), default=-1)
        end_char = _non_negative(span.get("end_char"), default=-1)
        if start_char >= 0 and end_char > start_char:
            return {"start_char": start_char, "end_char": end_char}

    highlight = chunk.get("highlight")
    if not isinstance(highlight, dict):
        return None
    if _text(highlight.get("status")).lower() != "exact":
        return None
    start_char = _non_negative(highlight.get("start_char"), default=-1)
    end_char = _non_negative(highlight.get("end_char"), default=-1)
    if start_char < 0 or end_char <= start_char:
        return None
    return {"start_char": start_char, "end_char": end_char}


def _trace_map(rows: list[object]) -> dict[str, dict[str, object]]:
    mapped: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = _text(row.get("chunk_id"))
        if not chunk_id:
            continue
        mapped[chunk_id] = row
    return mapped


def _chunk_map(rows: list[object]) -> dict[str, dict[str, object]]:
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = _text(row.get("chunk_id"))
        if not chunk_id:
            continue
        payload = dict(row)
        payload["chunk_id"] = chunk_id
        normalized_rows.append(payload)
    normalized_rows.sort(
        key=lambda item: (
            _text(item.get("doc_id") or item.get("document_id")),
            _positive(item.get("page_number"), default=1),
            _non_negative(item.get("chunk_index"), default=0),
            _text(item.get("chunk_id")),
        )
    )
    mapped: dict[str, dict[str, object]] = {}
    for row in normalized_rows:
        chunk_id = _text(row.get("chunk_id"))
        if chunk_id and chunk_id not in mapped:
            mapped[chunk_id] = row
    return mapped


def _chunk_ids(rows: list[object]) -> list[str]:
    normalized: list[str] = []
    for row in rows:
        chunk_id = _text(row)
        if not chunk_id:
            continue
        normalized.append(chunk_id)
    return normalized


def _answer_span(answer_text: str, *, chunk_id: str, start_at: int) -> tuple[dict[str, int], int]:
    token = f"[{chunk_id}]"
    index = answer_text.find(token, max(0, start_at))
    if index < 0:
        return {"start_char": 0, "end_char": 0}, start_at
    end = index + len(token)
    return {"start_char": index, "end_char": end}, end


def _chunk_doc_id(chunk_id: str) -> str:
    parts = chunk_id.split(":")
    if len(parts) > 1 and parts[0]:
        return parts[0]
    return chunk_id


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


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = ["map_answer_citations"]
