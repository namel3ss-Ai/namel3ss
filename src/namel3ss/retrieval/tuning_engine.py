from __future__ import annotations

from collections.abc import Mapping

from namel3ss.retrieval.ordering import rank_key
from namel3ss.retrieval.tuning import RetrievalTuning


def apply_retrieval_tuning(
    results: list[dict],
    *,
    tuning: RetrievalTuning,
    vector_scores: Mapping[str, float | None] | None,
    tie_break_chunk_id: bool,
    limit: int | None,
) -> list[dict]:
    if not tuning.explicit:
        return _apply_limit(results, limit)
    entries = _score_entries(
        results,
        vector_scores=vector_scores,
        semantic_weight=tuning.semantic_weight,
        tie_break_chunk_id=tie_break_chunk_id,
    )
    lexical_selected = _select_pool(entries, key="lexical_score", k=tuning.lexical_k)
    semantic_selected = _select_pool(entries, key="semantic_score", k=tuning.semantic_k)
    selected = _merge_selected(lexical_selected, semantic_selected)
    final_limit = tuning.final_top_k if tuning.final_top_k is not None else limit
    if final_limit is not None:
        selected = selected[:final_limit]
    return [dict(item["entry"]) for item in selected]


def build_tuning_summary(
    *,
    tuning: RetrievalTuning,
    results: list[dict],
    vector_scores: Mapping[str, float | None] | None,
    tie_break_chunk_id: bool,
) -> dict[str, object]:
    if not tuning.explicit:
        return tuning.as_dict()
    entries = _score_entries(
        results,
        vector_scores=vector_scores,
        semantic_weight=tuning.semantic_weight,
        tie_break_chunk_id=tie_break_chunk_id,
    )
    lexical_selected = _select_pool(entries, key="lexical_score", k=tuning.lexical_k)
    semantic_selected = _select_pool(entries, key="semantic_score", k=tuning.semantic_k)
    merged = _merge_selected(lexical_selected, semantic_selected)
    payload = tuning.as_dict()
    payload["counts"] = {
        "candidates": len(entries),
        "lexical_selected": len(lexical_selected),
        "semantic_selected": len(semantic_selected),
        "union_selected": len(merged),
    }
    return payload


def _score_entries(
    results: list[dict],
    *,
    vector_scores: Mapping[str, float | None] | None,
    semantic_weight: float,
    tie_break_chunk_id: bool,
) -> list[dict[str, object]]:
    if not results:
        return []
    max_overlap = max(_as_int(entry.get("keyword_overlap")) for entry in results)
    if max_overlap <= 0:
        max_overlap = 1
    scored: list[dict[str, object]] = []
    lexical_weight = round(1.0 - semantic_weight, 4)
    for index, entry in enumerate(results):
        lexical = _as_int(entry.get("keyword_overlap"))
        lexical_score = round(min(1.0, max(0.0, float(lexical) / float(max_overlap))), 4)
        chunk_id = str(entry.get("chunk_id") or "")
        semantic_score = 0.0
        if chunk_id and isinstance(vector_scores, Mapping):
            semantic_score = _as_score(vector_scores.get(chunk_id))
        combined = round((semantic_weight * semantic_score) + (lexical_weight * lexical_score), 4)
        scored.append(
            {
                "entry": dict(entry),
                "chunk_id": chunk_id,
                "lexical_score": lexical_score,
                "semantic_score": semantic_score,
                "combined_score": combined,
                "tie_key": rank_key(entry, index, tie_break_chunk_id=tie_break_chunk_id),
            }
        )
    return scored


def _select_pool(entries: list[dict[str, object]], *, key: str, k: int | None) -> list[dict[str, object]]:
    if not entries:
        return []
    if key not in {"lexical_score", "semantic_score"}:
        return []
    scored = list(entries)
    scored.sort(key=lambda item: (-_as_score(item.get(key)), item.get("tie_key")))
    if k is None:
        return scored
    if k <= 0:
        return []
    return scored[:k]


def _merge_selected(
    lexical_selected: list[dict[str, object]],
    semantic_selected: list[dict[str, object]],
) -> list[dict[str, object]]:
    union: dict[str, dict[str, object]] = {}
    for item in lexical_selected + semantic_selected:
        chunk_id = str(item.get("chunk_id") or "")
        if not chunk_id:
            continue
        existing = union.get(chunk_id)
        if existing is None:
            union[chunk_id] = item
            continue
        current = _as_score(existing.get("combined_score"))
        incoming = _as_score(item.get("combined_score"))
        if incoming > current:
            union[chunk_id] = item
            continue
        if incoming == current and item.get("tie_key") < existing.get("tie_key"):
            union[chunk_id] = item
    merged = list(union.values())
    merged.sort(key=lambda item: (-_as_score(item.get("combined_score")), item.get("tie_key")))
    return merged


def _apply_limit(results: list[dict], limit: int | None) -> list[dict]:
    if limit is None:
        return [dict(entry) for entry in results]
    return [dict(entry) for entry in results[:limit]]


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def _as_score(value: object) -> float:
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


__all__ = ["apply_retrieval_tuning", "build_tuning_summary"]
