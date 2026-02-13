from __future__ import annotations

from namel3ss.rag.determinism.json_policy import canonical_contract_copy


EXPLAIN_SCHEMA_VERSION = "rag.explain@1"


def build_retrieval_explain_payload(
    *,
    query: str,
    retrieval_results: object,
    retrieval_trace: object,
    retrieval_plan: object,
    retrieval_tuning: object,
    trust_score_details: object,
    retrieval_scope: object,
    schema_version: str = EXPLAIN_SCHEMA_VERSION,
) -> dict[str, object]:
    rows = retrieval_results if isinstance(retrieval_results, list) else []
    trace_rows = retrieval_trace if isinstance(retrieval_trace, list) else []
    return {
        "schema_version": _text(schema_version) or EXPLAIN_SCHEMA_VERSION,
        "query": _text(query),
        "retrieval_scope": _sanitize_scope(retrieval_scope),
        "retrieval_plan": _sanitize_dict(retrieval_plan),
        "retrieval_tuning": _sanitize_tuning(retrieval_tuning),
        "retrieval_trace": _build_trace_rows(rows=rows, trace_rows=trace_rows),
        "trust_score_details": _sanitize_dict(trust_score_details),
    }


def _build_trace_rows(*, rows: list[object], trace_rows: list[object]) -> list[dict[str, object]]:
    trace_map = _trace_map(trace_rows)
    normalized: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = _text(row.get("chunk_id"))
        if not chunk_id:
            continue
        trace = trace_map.get(chunk_id, {})
        reason_codes = row.get("reason_codes") if isinstance(row.get("reason_codes"), list) else []
        reason = _text(reason_codes[0]) if reason_codes else _text(trace.get("reason"))
        if not reason:
            reason = "retrieval"
        normalized.append(
            {
                "chunk_id": chunk_id,
                "document_id": _text(row.get("doc_id") or row.get("document_id") or trace.get("document_id") or trace.get("upload_id")),
                "ingestion_phase": _text(row.get("ingestion_phase") or trace.get("ingestion_phase")),
                "page_number": _positive_int(row.get("page_number") or trace.get("page_number"), default=1),
                "quality": _text(row.get("quality") or trace.get("quality")),
                "rank": _positive_int(row.get("rank"), default=1),
                "reason": reason,
                "score": _score(row.get("score") if row.get("score") is not None else trace.get("score")),
                "upload_id": _text(row.get("upload_id") or trace.get("upload_id")),
            }
        )

    normalized.sort(
        key=lambda row: (
            _positive_int(row.get("rank"), default=1),
            _text(row.get("document_id")),
            _positive_int(row.get("page_number"), default=1),
            _text(row.get("chunk_id")),
        )
    )
    return normalized


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


def _sanitize_tuning(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    return {
        "explicit": bool(data.get("explicit")),
        "final_top_k": _nullable_int(data.get("final_top_k")),
        "lexical_k": _nullable_int(data.get("lexical_k")),
        "semantic_k": _nullable_int(data.get("semantic_k")),
        "semantic_weight": _score(data.get("semantic_weight", 0.5)),
    }


def _sanitize_scope(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    requested = data.get("requested") if isinstance(data.get("requested"), dict) else {}
    collections = _string_list(requested.get("collections"))
    documents = _string_list(requested.get("documents"))
    resolved = _string_list(data.get("resolved_documents"))
    return {
        "active": bool(data.get("active")),
        "requested": {
            "collections": collections,
            "documents": documents,
        },
        "resolved_documents": resolved,
    }


def _sanitize_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return canonical_contract_copy(value)


def _string_list(value: object) -> list[str]:
    rows = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for row in rows:
        text = _text(row)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    normalized.sort()
    return normalized


def _score(value: object) -> float:
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


def _nullable_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


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


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "EXPLAIN_SCHEMA_VERSION",
    "build_retrieval_explain_payload",
]
