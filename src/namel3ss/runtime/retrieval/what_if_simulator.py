from __future__ import annotations

from collections.abc import Mapping


def simulate_ranking_from_trace(
    trace: Mapping[str, object] | None,
    *,
    params: Mapping[str, object] | None = None,
) -> dict[str, object]:
    rows = _normalize_rows(trace.get("final") if isinstance(trace, Mapping) else None)
    merged_params = _merged_params(trace, params)
    if not rows:
        return {"params": merged_params, "final": []}
    semantic_selected = _select_rows(rows, score_key="semantic_score", limit=_optional_int(merged_params.get("semantic_k")))
    lexical_selected = _select_rows(rows, score_key="lexical_score", limit=_optional_int(merged_params.get("lexical_k")))
    merged = _merge_rows(lexical_selected, semantic_selected)
    weighted = _apply_weight(merged, semantic_weight=_score(merged_params.get("semantic_weight")))
    final_sorted = _sort_final(weighted)
    final_limit = _optional_int(merged_params.get("final_top_k"))
    if final_limit is not None and final_limit >= 0:
        final_sorted = final_sorted[:final_limit]
    return {
        "params": merged_params,
        "final": [_public_row(row) for row in final_sorted],
    }


def _normalize_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "doc_id": str(item.get("doc_id") or ""),
                "title": str(item.get("title") or ""),
                "semantic_score": _score(item.get("semantic_score")),
                "lexical_score": _score(item.get("lexical_score")),
                "final_score": _score(item.get("final_score")),
                "matched_tags": _sorted_tags(item.get("matched_tags")),
                "_row_key": (str(item.get("doc_id") or ""), index),
            }
        )
    return rows


def _merged_params(
    trace: Mapping[str, object] | None,
    params: Mapping[str, object] | None,
) -> dict[str, object]:
    base = trace.get("params") if isinstance(trace, Mapping) and isinstance(trace.get("params"), Mapping) else {}
    merged: dict[str, object] = {
        "semantic_weight": _score(base.get("semantic_weight") if isinstance(base, Mapping) else 0.5),
        "semantic_k": _optional_int(base.get("semantic_k") if isinstance(base, Mapping) else None),
        "lexical_k": _optional_int(base.get("lexical_k") if isinstance(base, Mapping) else None),
        "final_top_k": _optional_int(base.get("final_top_k") if isinstance(base, Mapping) else None),
    }
    if isinstance(params, Mapping):
        for key in ("semantic_weight", "semantic_k", "lexical_k", "final_top_k"):
            if key not in params:
                continue
            if key == "semantic_weight":
                merged[key] = _score(params.get(key))
            else:
                merged[key] = _optional_int(params.get(key))
    return merged


def _select_rows(rows: list[dict[str, object]], *, score_key: str, limit: int | None) -> list[dict[str, object]]:
    ordered = list(rows)
    ordered.sort(
        key=lambda row: (
            -_score(row.get(score_key)),
            -_score(row.get("semantic_score")),
            -_score(row.get("lexical_score")),
            str(row.get("doc_id") or ""),
            row.get("_row_key"),
        )
    )
    if limit is None:
        return ordered
    if limit <= 0:
        return []
    return ordered[:limit]


def _merge_rows(first: list[dict[str, object]], second: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[tuple[str, int], dict[str, object]] = {}
    for row in [*first, *second]:
        key = row.get("_row_key")
        if not isinstance(key, tuple):
            continue
        merged[key] = row
    return list(merged.values())


def _apply_weight(rows: list[dict[str, object]], *, semantic_weight: float) -> list[dict[str, object]]:
    lexical_weight = round(1.0 - semantic_weight, 4)
    weighted: list[dict[str, object]] = []
    for row in rows:
        entry = dict(row)
        semantic = _score(entry.get("semantic_score"))
        lexical = _score(entry.get("lexical_score"))
        entry["final_score"] = round((semantic_weight * semantic) + (lexical_weight * lexical), 4)
        weighted.append(entry)
    return weighted


def _sort_final(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = list(rows)
    ordered.sort(
        key=lambda row: (
            -_score(row.get("final_score")),
            -_score(row.get("semantic_score")),
            -_score(row.get("lexical_score")),
            str(row.get("doc_id") or ""),
            row.get("_row_key"),
        )
    )
    return ordered


def _public_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "doc_id": str(row.get("doc_id") or ""),
        "title": str(row.get("title") or ""),
        "semantic_score": _score(row.get("semantic_score")),
        "lexical_score": _score(row.get("lexical_score")),
        "final_score": _score(row.get("final_score")),
        "matched_tags": _sorted_tags(row.get("matched_tags")),
    }


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if not isinstance(value, (int, float)):
        return 0.0
    number = float(value)
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return round(number, 4)


def _sorted_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    tags: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        tags.append(text)
    return sorted(tags)


__all__ = ["simulate_ranking_from_trace"]
