from __future__ import annotations

from namel3ss.rag.contracts.retrieval_result_model import build_retrieval_result_model
from namel3ss.rag.determinism.order_policy import sort_retrieval_results


RERANK_SCHEMA_VERSION = "rag.rerank@1"


def build_ranked_retrieval_results(
    *,
    results: object,
    retrieval_trace: object,
) -> list[dict[str, object]]:
    trace_map = _trace_map(retrieval_trace)
    rows = [entry for entry in (results or []) if isinstance(entry, dict)]
    sortable: list[dict[str, object]] = []
    for row in rows:
        chunk_id = _text(row.get("chunk_id"))
        trace = trace_map.get(chunk_id, row)
        sortable.append(
            {
                "chunk_id": chunk_id,
                "doc_id": _text(row.get("doc_id") or row.get("document_id") or row.get("upload_id") or trace.get("document_id") or trace.get("upload_id")),
                "page_number": _positive(row.get("page_number") or trace.get("page_number"), default=1),
                "score": _score(row.get("score") if row.get("score") is not None else trace.get("score")),
                "rerank_score": _score(
                    row.get("rerank_score") if row.get("rerank_score") is not None else _raw_score(trace)
                ),
                "reason": _text(row.get("reason") or trace.get("reason")),
                "ingestion_phase": _text(row.get("ingestion_phase") or trace.get("ingestion_phase")),
                "quality": _text(row.get("quality") or trace.get("quality")),
                "upload_id": _text(row.get("upload_id") or trace.get("upload_id")),
            }
        )

    ordered = sort_retrieval_results(sortable)
    contracts: list[dict[str, object]] = []
    for index, row in enumerate(ordered, start=1):
        reason_codes = [_text(row.get("reason"))] if _text(row.get("reason")) else []
        contract = build_retrieval_result_model(
            rank=index,
            chunk_id=_text(row.get("chunk_id")),
            doc_id=_text(row.get("doc_id")),
            page_number=_positive(row.get("page_number"), default=1),
            score=_score(row.get("score")),
            rerank_score=_score(row.get("rerank_score")),
            reason_codes=reason_codes,
        )
        if _text(row.get("ingestion_phase")):
            contract["ingestion_phase"] = _text(row.get("ingestion_phase"))
        if _text(row.get("quality")):
            contract["quality"] = _text(row.get("quality"))
        if _text(row.get("upload_id")):
            contract["upload_id"] = _text(row.get("upload_id"))
        contracts.append(contract)
    return contracts


def _trace_map(rows: object) -> dict[str, dict[str, object]]:
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = _text(row.get("chunk_id"))
        if not chunk_id:
            continue
        mapped[chunk_id] = row
    return mapped


def _raw_score(trace: dict[str, object]) -> object:
    components = trace.get("score_components")
    if isinstance(components, dict):
        return components.get("raw_score", trace.get("score"))
    return trace.get("score")


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
    return round(number, 6)


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


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "RERANK_SCHEMA_VERSION",
    "build_ranked_retrieval_results",
]
