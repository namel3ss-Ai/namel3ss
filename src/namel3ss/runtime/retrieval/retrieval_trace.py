from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.retrieval.retrieval_ranker import score_retrieval_entries


def build_retrieval_trace(
    results: object,
    *,
    ingestion_status: Mapping[str, object] | None = None,
    vector_scores: Mapping[str, float | None] | None = None,
) -> list[dict[str, object]]:
    entries = _normalize_results(results, vector_scores=vector_scores)
    if not entries:
        return []
    scored_entries = score_retrieval_entries(entries)
    score_by_chunk = {
        str(entry.get("chunk_id") or ""): entry
        for entry in scored_entries
        if isinstance(entry, dict) and isinstance(entry.get("chunk_id"), str)
    }
    reports = ingestion_status if isinstance(ingestion_status, Mapping) else {}
    trace: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        chunk_id = str(entry.get("chunk_id") or "")
        upload_id = str(entry.get("upload_id") or "")
        report = reports.get(upload_id)
        fallback_used = _fallback_used(report)
        reason = _trace_reason(entry, fallback_used=fallback_used)
        score_entry = score_by_chunk.get(chunk_id) or {}
        trace_entry: dict[str, object] = {
            "chunk_id": chunk_id,
            "document_id": str(entry.get("document_id") or ""),
            "page_number": _coerce_page_number(entry.get("page_number")),
            "score": _coerce_float(score_entry.get("score")),
            "rank": index + 1,
            "reason": reason,
            "upload_id": upload_id,
            "ingestion_phase": str(entry.get("ingestion_phase") or ""),
            "quality": str(entry.get("quality") or "pass"),
        }
        components = score_entry.get("components")
        if isinstance(components, dict):
            trace_entry["score_components"] = dict(components)
        trace.append(trace_entry)
    return trace


def _normalize_results(
    value: object,
    *,
    vector_scores: Mapping[str, float | None] | None,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        chunk_id = str(entry.get("chunk_id") or "")
        if chunk_id and isinstance(vector_scores, Mapping):
            entry["vector_score"] = vector_scores.get(chunk_id)
        normalized.append(entry)
    return normalized


def _trace_reason(entry: Mapping[str, object], *, fallback_used: bool) -> str:
    if fallback_used:
        return "fallback_inclusion"
    quality = str(entry.get("quality") or "")
    if quality == "warn":
        return "low_quality_inclusion"
    keyword_overlap = _coerce_int(entry.get("keyword_overlap"))
    vector_score = _coerce_float(entry.get("vector_score"))
    if vector_score > 0 and keyword_overlap <= 0:
        return "semantic_match"
    if keyword_overlap > 0:
        return "keyword_match"
    return "deterministic_rank"


def _fallback_used(report: object) -> bool:
    if not isinstance(report, Mapping):
        return False
    value = report.get("fallback_used")
    return isinstance(value, str) and value.strip().lower() == "ocr"


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def _coerce_page_number(value: object) -> int:
    number = _coerce_int(value)
    if number > 0:
        return number
    return 0


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        if number < 0.0:
            return 0.0
        if number > 1.0:
            return 1.0
        return round(number, 4)
    return 0.0


__all__ = ["build_retrieval_trace"]
