from __future__ import annotations

from collections.abc import Mapping


def build_trust_score_details(
    *,
    retrieval_trace: object,
    ingestion_status: Mapping[str, object] | None = None,
) -> dict[str, object]:
    trace_entries = _trace_entries(retrieval_trace)
    trace_count = len(trace_entries)
    if trace_count == 0:
        return {
            "formula_version": "rag_trust@1",
            "score": 0.0,
            "level": "low",
            "inputs": {
                "retrieval_count": 0,
                "avg_retrieval_score": 0.0,
                "score_spread": 0.0,
                "source_diversity": 0.0,
                "coverage": 0.0,
                "warn_count": 0,
                "fallback_count": 0,
                "ingestion_warn_count": 0,
            },
            "components": [],
            "penalties": [],
        }

    scores = [_score(entry.get("score")) for entry in trace_entries]
    avg_score = sum(scores) / float(trace_count)
    score_spread = max(scores) - min(scores)

    document_ids = {str(entry.get("document_id") or "") for entry in trace_entries if str(entry.get("document_id") or "")}
    source_diversity = len(document_ids) / float(trace_count)
    coverage = min(1.0, float(trace_count) / 4.0)

    warn_count = sum(1 for entry in trace_entries if str(entry.get("quality") or "") == "warn")
    fallback_count = sum(1 for entry in trace_entries if str(entry.get("reason") or "") == "fallback_inclusion")

    reports = ingestion_status if isinstance(ingestion_status, Mapping) else {}
    selected_upload_ids = {str(entry.get("upload_id") or "") for entry in trace_entries if str(entry.get("upload_id") or "")}
    ingestion_warn_count = 0
    for upload_id in selected_upload_ids:
        report = reports.get(upload_id)
        if not isinstance(report, Mapping):
            continue
        status = str(report.get("status") or "")
        if status == "warn":
            ingestion_warn_count += 1

    warn_penalty = min(0.25, (warn_count / float(trace_count)) * 0.2)
    fallback_penalty = min(0.2, (fallback_count / float(trace_count)) * 0.15)
    ingestion_penalty = min(0.2, ingestion_warn_count * 0.03)
    total_penalty = warn_penalty + fallback_penalty + ingestion_penalty

    component_avg = 0.55 * avg_score
    component_diversity = 0.35 * source_diversity
    component_coverage = 0.10 * coverage
    raw_score = component_avg + component_diversity + component_coverage - total_penalty
    score = round(_clamp01(raw_score), 4)

    return {
        "formula_version": "rag_trust@1",
        "score": score,
        "level": _level(score),
        "inputs": {
            "retrieval_count": trace_count,
            "avg_retrieval_score": round(avg_score, 4),
            "score_spread": round(score_spread, 4),
            "source_diversity": round(source_diversity, 4),
            "coverage": round(coverage, 4),
            "warn_count": warn_count,
            "fallback_count": fallback_count,
            "ingestion_warn_count": ingestion_warn_count,
        },
        "components": [
            {
                "name": "avg_retrieval_score",
                "weight": 0.55,
                "value": round(avg_score, 4),
                "contribution": round(component_avg, 4),
            },
            {
                "name": "source_diversity",
                "weight": 0.35,
                "value": round(source_diversity, 4),
                "contribution": round(component_diversity, 4),
            },
            {
                "name": "coverage",
                "weight": 0.10,
                "value": round(coverage, 4),
                "contribution": round(component_coverage, 4),
            },
        ],
        "penalties": [
            {"name": "warn_quality", "value": warn_count, "amount": round(warn_penalty, 4)},
            {"name": "ocr_fallback", "value": fallback_count, "amount": round(fallback_penalty, 4)},
            {"name": "ingestion_warn", "value": ingestion_warn_count, "amount": round(ingestion_penalty, 4)},
        ],
    }


def _trace_entries(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    entries: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            entries.append(item)
    return entries


def _score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        return _clamp01(number)
    return 0.0


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _level(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


__all__ = ["build_trust_score_details"]
