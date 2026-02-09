from __future__ import annotations

from collections.abc import Mapping


def build_retrieval_plan(
    *,
    query: str,
    state: Mapping[str, object] | None,
    tier: Mapping[str, object] | None,
    limit: int | None,
    ordering: str,
    warn_policy: Mapping[str, object] | None,
    warn_allowed: bool,
    preferred_quality: str,
    selected_results: list[dict[str, object]],
    retrieval_trace: list[dict[str, object]],
) -> dict[str, object]:
    scope = _active_scope(state)
    tier_info = _tier_summary(tier)
    selected_chunk_ids = [str(entry.get("chunk_id") or "") for entry in retrieval_trace if isinstance(entry, dict)]
    selected_chunk_ids = [entry for entry in selected_chunk_ids if entry]
    selected_scores = [
        {
            "chunk_id": str(entry.get("chunk_id") or ""),
            "score": _coerce_score(entry.get("score")),
        }
        for entry in retrieval_trace
        if isinstance(entry, dict) and isinstance(entry.get("chunk_id"), str)
    ]
    filters = [
        {
            "name": "quality_gate",
            "preferred_quality": preferred_quality if preferred_quality in {"pass", "warn"} else "pass",
            "warn_allowed": bool(warn_allowed),
            "policy": _policy_summary(warn_policy),
        },
        {
            "name": "scope",
            "source": scope["source"],
            "active": scope["active"],
            "applied": scope["applied"],
        },
    ]
    return {
        "query": query,
        "scope": scope,
        "tier": tier_info,
        "filters": filters,
        "cutoffs": {
            "limit": _normalize_limit(limit),
            "candidate_count": tier_info["candidate_count"],
            "selected_count": len(selected_results),
        },
        "ordering": ordering,
        "selected_chunk_ids": selected_chunk_ids,
        "selected_scores": selected_scores,
    }


def _active_scope(state: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(state, Mapping):
        return {"source": "state.active_docs", "active": [], "applied": False}
    active_docs = state.get("active_docs")
    active = _normalize_scope_values(active_docs)
    if active:
        return {"source": "state.active_docs", "active": active, "applied": True}
    retrieval = state.get("retrieval")
    if isinstance(retrieval, Mapping):
        active_scope = _normalize_scope_values(retrieval.get("active_scope"))
        if active_scope:
            return {"source": "state.retrieval.active_scope", "active": active_scope, "applied": True}
    return {"source": "state.active_docs", "active": [], "applied": False}


def _normalize_scope_values(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    ordered: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _tier_summary(value: Mapping[str, object] | None) -> dict[str, object]:
    tier = value if isinstance(value, Mapping) else {}
    counts = tier.get("counts")
    counts_map = counts if isinstance(counts, Mapping) else {}
    deep_count = _coerce_non_negative_int(counts_map.get("deep"))
    quick_count = _coerce_non_negative_int(counts_map.get("quick"))
    return {
        "requested": str(tier.get("requested") or "auto"),
        "selected": str(tier.get("selected") or "none"),
        "reason": str(tier.get("reason") or "unknown"),
        "available": _normalize_scope_values(tier.get("available")),
        "counts": {
            "deep": deep_count,
            "quick": quick_count,
        },
        "candidate_count": deep_count + quick_count,
    }


def _policy_summary(value: Mapping[str, object] | None) -> dict[str, str]:
    policy = value if isinstance(value, Mapping) else {}
    return {
        "action": str(policy.get("action") or "retrieval.include_warn"),
        "decision": str(policy.get("decision") or "unknown"),
        "reason": str(policy.get("reason") or ""),
    }


def _normalize_limit(value: int | None) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _coerce_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value >= 0 else 0
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed >= 0 else 0
    return 0


def _coerce_score(value: object) -> float:
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


__all__ = ["build_retrieval_plan"]
