from __future__ import annotations

from namel3ss.rag.contracts.trace_model import build_trace_model
from namel3ss.rag.determinism.json_policy import canonical_contract_hash


STREAM_EVENT_SCHEMA_VERSION = "rag.stream_event@1"

STREAM_EVENT_TOKEN = "token"
STREAM_EVENT_CITATION_ADD = "citation_add"
STREAM_EVENT_TRACE = "trace_event"
STREAM_EVENT_FINAL = "final"

_ALLOWED_EVENT_TYPES = {
    STREAM_EVENT_TOKEN,
    STREAM_EVENT_CITATION_ADD,
    STREAM_EVENT_TRACE,
    STREAM_EVENT_FINAL,
}
_EVENT_TYPE_ORDER = {
    STREAM_EVENT_TOKEN: 0,
    STREAM_EVENT_CITATION_ADD: 1,
    STREAM_EVENT_TRACE: 2,
    STREAM_EVENT_FINAL: 3,
}


def normalize_stream_events(events: object) -> list[dict[str, object]]:
    rows = events if isinstance(events, list) else []
    normalized: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        event_type = _event_type(row.get("event_type"))
        if event_type not in _ALLOWED_EVENT_TYPES:
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        normalized.append(
            {
                "event_type": event_type,
                "payload": _sanitize(payload),
                "schema_version": STREAM_EVENT_SCHEMA_VERSION,
                "sequence": _non_negative_int(row.get("sequence"), default=0),
            }
        )

    normalized.sort(
        key=lambda row: (
            _non_negative_int(row.get("sequence"), default=0),
            _EVENT_TYPE_ORDER.get(_event_type(row.get("event_type")), 999),
            canonical_contract_hash(row.get("payload") if isinstance(row.get("payload"), dict) else {}),
        )
    )

    rows_with_sequence: list[dict[str, object]] = []
    for index, row in enumerate(normalized, start=1):
        event_type = _event_type(row.get("event_type"))
        if event_type == STREAM_EVENT_FINAL and index != len(normalized):
            continue
        rows_with_sequence.append(
            {
                "event_type": event_type,
                "payload": _sanitize(row.get("payload") if isinstance(row.get("payload"), dict) else {}),
                "schema_version": STREAM_EVENT_SCHEMA_VERSION,
                "sequence": index,
            }
        )

    if not rows_with_sequence or _event_type(rows_with_sequence[-1].get("event_type")) != STREAM_EVENT_FINAL:
        rows_with_sequence.append(
            {
                "event_type": STREAM_EVENT_FINAL,
                "payload": {},
                "schema_version": STREAM_EVENT_SCHEMA_VERSION,
                "sequence": len(rows_with_sequence) + 1,
            }
        )
    return rows_with_sequence


def build_answer_stream_events(
    *,
    answer_text: str,
    citations: object,
    retrieval_trace: object,
) -> list[dict[str, object]]:
    text = _text(answer_text)
    tokens = [token for token in text.split() if token]
    rows: list[dict[str, object]] = []
    for token in tokens:
        rows.append(
            {
                "event_type": STREAM_EVENT_TOKEN,
                "payload": {"token": token},
            }
        )

    citation_rows = citations if isinstance(citations, list) else []
    for row in _normalize_citations(citation_rows):
        rows.append(
            {
                "event_type": STREAM_EVENT_CITATION_ADD,
                "payload": row,
            }
        )

    trace_rows = retrieval_trace if isinstance(retrieval_trace, list) else []
    rows.append(
        {
            "event_type": STREAM_EVENT_TRACE,
            "payload": {
                "retrieval_count": len([row for row in trace_rows if isinstance(row, dict)]),
                "token_count": len(tokens),
            },
        }
    )
    rows.append(
        {
            "event_type": STREAM_EVENT_FINAL,
            "payload": {
                "answer_chars": len(text),
                "citation_count": len(_normalize_citations(citation_rows)),
            },
        }
    )
    return normalize_stream_events(rows)


def build_observability_trace_model(
    *,
    query: str,
    retrieval_config: dict[str, object],
    retrieval_results: object,
    retrieval_scope: object,
    retrieval_plan: object,
    stream_events: object,
) -> dict[str, object]:
    rows = retrieval_results if isinstance(retrieval_results, list) else []
    chunk_ids = [
        _text(row.get("chunk_id"))
        for row in rows
        if isinstance(row, dict) and _text(row.get("chunk_id"))
    ]
    stream_rows = list(stream_events) if isinstance(stream_events, list) else []
    stream_rows.append(
        {
            "event_type": STREAM_EVENT_TRACE,
            "payload": {
                "retrieval_plan": _sanitize(retrieval_plan if isinstance(retrieval_plan, dict) else {}),
            },
            "sequence": _non_negative_int(len(stream_rows), default=0),
        }
    )
    normalized_events = normalize_stream_events(stream_rows)
    return build_trace_model(
        input_payload={
            "query": _text(query),
            "retrieval_scope": _sanitize(retrieval_scope if isinstance(retrieval_scope, dict) else {}),
        },
        retrieval_config=_sanitize(retrieval_config if isinstance(retrieval_config, dict) else {}),
        retrieved_chunk_ids=chunk_ids,
        events=[
            {
                "event_type": _event_type(entry.get("event_type")),
                "payload": _sanitize(entry.get("payload") if isinstance(entry.get("payload"), dict) else {}),
                "sequence": _non_negative_int(entry.get("sequence"), default=0),
            }
            for entry in normalized_events
        ],
    )


def _normalize_citations(value: list[object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        citation_id = _text(row.get("citation_id"))
        chunk_id = _text(row.get("chunk_id"))
        if not citation_id or not chunk_id:
            continue
        rows.append(
            {
                "citation_id": citation_id,
                "chunk_id": chunk_id,
                "doc_id": _text(row.get("doc_id")),
                "page_number": _positive_int(row.get("page_number"), default=1),
            }
        )
    rows.sort(key=lambda row: (_text(row.get("citation_id")), _text(row.get("chunk_id"))))
    return rows


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _sanitize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


def _event_type(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


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


__all__ = [
    "STREAM_EVENT_CITATION_ADD",
    "STREAM_EVENT_FINAL",
    "STREAM_EVENT_SCHEMA_VERSION",
    "STREAM_EVENT_TOKEN",
    "STREAM_EVENT_TRACE",
    "build_answer_stream_events",
    "build_observability_trace_model",
    "normalize_stream_events",
]
