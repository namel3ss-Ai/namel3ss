from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.retrieval.retrieval_plan import build_retrieval_plan
from namel3ss.runtime.retrieval.retrieval_trace import build_retrieval_trace
from namel3ss.runtime.trust.trust_score import build_trust_score_details


def build_retrieval_artifacts(
    *,
    query: str,
    state: Mapping[str, object] | None,
    tier: Mapping[str, object] | None,
    limit: int | None,
    ordering: str,
    warn_policy: Mapping[str, object] | None,
    warn_allowed: bool,
    preferred_quality: str,
    results: object,
    vector_scores: Mapping[str, float | None] | None = None,
) -> dict[str, object]:
    selected_results = _selected_results(results)
    ingestion_status = _ingestion_status_map(state)
    retrieval_trace = build_retrieval_trace(
        selected_results,
        ingestion_status=ingestion_status,
        vector_scores=vector_scores,
    )
    retrieval_plan = build_retrieval_plan(
        query=query,
        state=state,
        tier=tier,
        limit=limit,
        ordering=ordering,
        warn_policy=warn_policy,
        warn_allowed=warn_allowed,
        preferred_quality=preferred_quality,
        selected_results=selected_results,
        retrieval_trace=retrieval_trace,
    )
    trust_score_details = build_trust_score_details(
        retrieval_trace=retrieval_trace,
        ingestion_status=ingestion_status,
    )
    return {
        "retrieval_plan": retrieval_plan,
        "retrieval_trace": retrieval_trace,
        "trust_score_details": trust_score_details,
    }


def _selected_results(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    entries: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            entries.append(dict(item))
    return entries


def _ingestion_status_map(state: Mapping[str, object] | None) -> Mapping[str, object]:
    if not isinstance(state, Mapping):
        return {}
    ingestion = state.get("ingestion")
    if isinstance(ingestion, Mapping):
        return ingestion
    return {}


__all__ = ["build_retrieval_artifacts"]
