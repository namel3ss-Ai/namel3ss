from __future__ import annotations

from collections.abc import Iterable

_SCORE_PRECISION = 4


def score_retrieval_entries(entries: Iterable[dict]) -> list[dict[str, object]]:
    normalized = [entry for entry in entries if isinstance(entry, dict)]
    if not normalized:
        return []
    max_keyword_overlap = _max_keyword_overlap(normalized)
    scored: list[dict[str, object]] = []
    for entry in normalized:
        chunk_id = _as_text(entry.get("chunk_id"))
        score, components = normalize_retrieval_score(
            keyword_overlap=_as_int(entry.get("keyword_overlap")),
            vector_score=_as_float(entry.get("vector_score")),
            ingestion_phase=_as_text(entry.get("ingestion_phase")),
            quality=_as_text(entry.get("quality")) or "pass",
            max_keyword_overlap=max_keyword_overlap,
        )
        scored.append(
            {
                "chunk_id": chunk_id,
                "score": score,
                "components": components,
            }
        )
    return scored


def normalize_retrieval_score(
    *,
    keyword_overlap: int,
    vector_score: float | None,
    ingestion_phase: str,
    quality: str,
    max_keyword_overlap: int,
) -> tuple[float, dict[str, float]]:
    keyword_component = _keyword_component(keyword_overlap, max_keyword_overlap=max_keyword_overlap)
    semantic_component = _semantic_component(vector_score)
    phase_component = 0.1 if ingestion_phase == "deep" else 0.0
    quality_penalty = 0.15 if quality == "warn" else 0.0
    raw_score = (0.6 * keyword_component) + (0.3 * semantic_component) + phase_component - quality_penalty
    bounded_score = round(_clamp01(raw_score), _SCORE_PRECISION)
    components = {
        "keyword_component": round(keyword_component, _SCORE_PRECISION),
        "semantic_component": round(semantic_component, _SCORE_PRECISION),
        "phase_component": round(phase_component, _SCORE_PRECISION),
        "quality_penalty": round(quality_penalty, _SCORE_PRECISION),
        "raw_score": round(raw_score, _SCORE_PRECISION),
    }
    return bounded_score, components


def _max_keyword_overlap(entries: Iterable[dict]) -> int:
    max_overlap = 0
    for entry in entries:
        overlap = _as_int(entry.get("keyword_overlap"))
        if overlap > max_overlap:
            max_overlap = overlap
    return max(max_overlap, 1)


def _keyword_component(keyword_overlap: int, *, max_keyword_overlap: int) -> float:
    if max_keyword_overlap <= 0:
        return 0.0
    if keyword_overlap <= 0:
        return 0.0
    return _clamp01(float(keyword_overlap) / float(max_keyword_overlap))


def _semantic_component(vector_score: float | None) -> float:
    if vector_score is None:
        return 0.0
    return _clamp01(vector_score)


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _as_text(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text
    return ""


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


__all__ = ["normalize_retrieval_score", "score_retrieval_entries"]
