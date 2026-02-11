from __future__ import annotations

from collections.abc import Mapping

TRACE_TIE_BREAKER = "final_score desc, semantic_score desc, lexical_score desc, doc_id asc"


def build_retrieval_trace_contract(
    *,
    query: str,
    tuning: object,
    filter_tags: list[str] | None,
    results: list[dict],
    vector_scores: Mapping[str, float | None] | None,
) -> dict[str, object]:
    candidates = [entry for entry in results if isinstance(entry, dict)]
    rows = _build_rows(candidates, tuning=tuning, vector_scores=vector_scores)
    semantic = _sort_rows(rows, mode="semantic")
    lexical = _sort_rows(rows, mode="lexical")
    final = _sort_rows(rows, mode="final")
    return {
        "query": str(query or ""),
        "params": _params_snapshot(tuning),
        "filter_tags": _sorted_tags(filter_tags),
        "semantic": [_public_row(row) for row in semantic],
        "lexical": [_public_row(row) for row in lexical],
        "final": [_public_row(row) for row in final],
        "tie_breaker": TRACE_TIE_BREAKER,
    }


def _build_rows(
    entries: list[dict],
    *,
    tuning: object,
    vector_scores: Mapping[str, float | None] | None,
) -> list[dict[str, object]]:
    if not entries:
        return []
    lexical_max = max((_keyword_overlap(entry) for entry in entries), default=0)
    if lexical_max <= 0:
        lexical_max = 1
    semantic_weight = _semantic_weight(tuning)
    lexical_weight = round(1.0 - semantic_weight, 4)
    rows: list[dict[str, object]] = []
    for entry in entries:
        chunk_id = str(entry.get("chunk_id") or "")
        doc_id = str(entry.get("document_id") or entry.get("upload_id") or chunk_id)
        semantic_score = _semantic_score(entry, vector_scores=vector_scores)
        lexical_score = round(float(_keyword_overlap(entry)) / float(lexical_max), 4)
        final_score = round((semantic_weight * semantic_score) + (lexical_weight * lexical_score), 4)
        rows.append(
            {
                "doc_id": doc_id,
                "title": str(entry.get("source_name") or doc_id or "source"),
                "semantic_score": semantic_score,
                "lexical_score": lexical_score,
                "final_score": final_score,
                "matched_tags": _sorted_tags(entry.get("matched_tags") or entry.get("tags")),
                "_chunk_id": chunk_id,
            }
        )
    return rows


def _sort_rows(rows: list[dict[str, object]], *, mode: str) -> list[dict[str, object]]:
    ordered = [dict(row) for row in rows]
    if mode == "semantic":
        ordered.sort(
            key=lambda row: (
                -_score(row.get("semantic_score")),
                -_score(row.get("lexical_score")),
                str(row.get("doc_id") or ""),
                str(row.get("_chunk_id") or ""),
            )
        )
        return ordered
    if mode == "lexical":
        ordered.sort(
            key=lambda row: (
                -_score(row.get("lexical_score")),
                -_score(row.get("semantic_score")),
                str(row.get("doc_id") or ""),
                str(row.get("_chunk_id") or ""),
            )
        )
        return ordered
    ordered.sort(
        key=lambda row: (
            -_score(row.get("final_score")),
            -_score(row.get("semantic_score")),
            -_score(row.get("lexical_score")),
            str(row.get("doc_id") or ""),
            str(row.get("_chunk_id") or ""),
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


def _params_snapshot(tuning: object) -> dict[str, object]:
    if isinstance(tuning, Mapping):
        source = tuning
    else:
        source = {}
    return {
        "semantic_weight": _semantic_weight(tuning),
        "semantic_k": _optional_int(source.get("semantic_k") if isinstance(source, Mapping) else getattr(tuning, "semantic_k", None)),
        "lexical_k": _optional_int(source.get("lexical_k") if isinstance(source, Mapping) else getattr(tuning, "lexical_k", None)),
        "final_top_k": _optional_int(
            source.get("final_top_k") if isinstance(source, Mapping) else getattr(tuning, "final_top_k", None)
        ),
    }


def _semantic_weight(tuning: object) -> float:
    value = getattr(tuning, "semantic_weight", None)
    if value is None and isinstance(tuning, Mapping):
        value = tuning.get("semantic_weight")
    return _score(value if value is not None else 0.5)


def _semantic_score(entry: Mapping[str, object], *, vector_scores: Mapping[str, float | None] | None) -> float:
    explicit = entry.get("semantic_score")
    if isinstance(explicit, (int, float)) and not isinstance(explicit, bool):
        return _score(explicit)
    chunk_id = str(entry.get("chunk_id") or "")
    if chunk_id and isinstance(vector_scores, Mapping):
        return _score(vector_scores.get(chunk_id))
    return 0.0


def _keyword_overlap(entry: Mapping[str, object]) -> int:
    value = entry.get("keyword_overlap")
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed > 0 else 0
    return 0


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


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _sorted_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
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


__all__ = ["TRACE_TIE_BREAKER", "build_retrieval_trace_contract"]
