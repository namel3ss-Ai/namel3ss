from __future__ import annotations

from collections.abc import Mapping


def build_preview_rows(
    results: list[dict],
    *,
    vector_scores: Mapping[str, float | None] | None,
    semantic_weight: float,
) -> list[dict[str, object]]:
    entries = [entry for entry in results if isinstance(entry, dict)]
    if not entries:
        return []
    lexical_max = max((_coerce_non_negative_int(entry.get("keyword_overlap")) for entry in entries), default=0)
    if lexical_max <= 0:
        lexical_max = 1
    semantic_weight = _clamp_score(semantic_weight)
    lexical_weight = round(1.0 - semantic_weight, 4)
    rows: list[dict[str, object]] = []
    for entry in entries:
        chunk_id = str(entry.get("chunk_id") or "")
        document_id = str(entry.get("document_id") or entry.get("upload_id") or chunk_id)
        lexical_score = round(
            _coerce_non_negative_int(entry.get("keyword_overlap")) / float(lexical_max),
            4,
        )
        semantic_score = _semantic_score(entry, vector_scores=vector_scores)
        final_score = round((semantic_weight * semantic_score) + (lexical_weight * lexical_score), 4)
        title = str(entry.get("source_name") or document_id or "source")
        rows.append(
            {
                "doc_id": document_id,
                "title": title,
                "semantic_score": semantic_score,
                "lexical_score": lexical_score,
                "final_score": final_score,
                "matched_tags": _sorted_tags(entry.get("matched_tags")),
                "_chunk_id": chunk_id,
            }
        )
    rows.sort(
        key=lambda item: (
            -_clamp_score(item.get("final_score")),
            -_clamp_score(item.get("semantic_score")),
            -_clamp_score(item.get("lexical_score")),
            str(item.get("doc_id") or ""),
            str(item.get("_chunk_id") or ""),
        )
    )
    return [_public_row(row) for row in rows]


def _public_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "doc_id": str(row.get("doc_id") or ""),
        "title": str(row.get("title") or ""),
        "semantic_score": _clamp_score(row.get("semantic_score")),
        "lexical_score": _clamp_score(row.get("lexical_score")),
        "final_score": _clamp_score(row.get("final_score")),
        "matched_tags": _sorted_tags(row.get("matched_tags")),
    }


def _semantic_score(entry: Mapping[str, object], *, vector_scores: Mapping[str, float | None] | None) -> float:
    explicit = entry.get("semantic_score")
    if isinstance(explicit, (int, float)) and not isinstance(explicit, bool):
        return _clamp_score(explicit)
    chunk_id = str(entry.get("chunk_id") or "")
    if chunk_id and isinstance(vector_scores, Mapping):
        return _clamp_score(vector_scores.get(chunk_id))
    return 0.0


def _sorted_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    tags: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        tags.append(text)
    return sorted(tags)


def _coerce_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed > 0 else 0
    return 0


def _clamp_score(value: object) -> float:
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


__all__ = ["build_preview_rows"]

