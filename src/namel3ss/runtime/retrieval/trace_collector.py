from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.retrieval.trace_contract import build_retrieval_trace_contract


def diagnostics_trace_enabled(capabilities: tuple[str, ...] | list[str] | None) -> bool:
    return "diagnostics.trace" in set(capabilities or ())


def collect_retrieval_trace(
    *,
    enabled: bool,
    query: str,
    tuning: object,
    filter_tags: list[str] | None,
    results: list[dict],
    vector_scores: Mapping[str, float | None] | None,
) -> dict[str, object] | None:
    if not enabled:
        return None
    return build_retrieval_trace_contract(
        query=query,
        tuning=tuning,
        filter_tags=filter_tags,
        results=results,
        vector_scores=vector_scores,
    )


__all__ = ["collect_retrieval_trace", "diagnostics_trace_enabled"]
