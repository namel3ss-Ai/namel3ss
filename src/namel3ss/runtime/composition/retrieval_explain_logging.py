from __future__ import annotations

from pathlib import Path

_IMAGE_EXTENSIONS = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
_AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}


def build_retrieval_explain_metadata(report: dict[str, object]) -> dict[str, object]:
    results = _dict_list(report.get("results"))
    explain = report.get("explain")
    explain_candidates = _dict_list(explain.get("candidates")) if isinstance(explain, dict) else []

    selected = [_selected_chunk_payload(item) for item in results]
    selected_by_chunk = {item["chunk_id"]: item for item in selected if item.get("chunk_id")}

    candidate_chunks: list[dict[str, object]] = []
    scores: list[dict[str, object]] = []
    for candidate in explain_candidates:
        chunk_id = _safe_string(candidate.get("chunk_id"))
        selected_item = selected_by_chunk.get(chunk_id)
        modality = (
            str(selected_item.get("modality") or "text")
            if isinstance(selected_item, dict)
            else _infer_modality_from_source(None)
        )
        keyword_overlap = _safe_int(candidate.get("keyword_overlap"))
        vector_score = _safe_float(candidate.get("vector_score"))
        score = vector_score if vector_score is not None else keyword_overlap
        row = {
            "doc_id": selected_item.get("doc_id") if isinstance(selected_item, dict) else None,
            "chunk_id": chunk_id,
            "page_number": _safe_int(candidate.get("page_number")),
            "score": score,
            "source_url": selected_item.get("source_url") if isinstance(selected_item, dict) else None,
            "modality": modality,
            "decision": _safe_string(candidate.get("decision")),
            "reason": _safe_string(candidate.get("reason")),
            "keyword_overlap": keyword_overlap,
            "vector_score": vector_score,
        }
        candidate_chunks.append(row)
        scores.append(
            {
                "chunk_id": chunk_id,
                "score": score,
                "keyword_overlap": keyword_overlap,
                "vector_score": vector_score,
                "modality": modality,
            }
        )

    if not candidate_chunks and selected:
        for item in selected:
            candidate_chunks.append(
                {
                    "doc_id": item.get("doc_id"),
                    "chunk_id": item.get("chunk_id"),
                    "page_number": item.get("page_number"),
                    "score": item.get("score"),
                    "source_url": item.get("source_url"),
                    "modality": item.get("modality"),
                    "decision": "selected",
                    "reason": "top_k",
                    "keyword_overlap": item.get("score"),
                    "vector_score": None,
                }
            )
            scores.append(
                {
                    "chunk_id": item.get("chunk_id"),
                    "score": item.get("score"),
                    "keyword_overlap": item.get("score"),
                    "vector_score": None,
                    "modality": item.get("modality"),
                }
            )

    modalities = [str(item.get("modality") or "text") for item in selected or candidate_chunks]
    modality = _summarize_modality(modalities)
    top_chunk = selected[0] if selected else None
    tuning = report.get("retrieval_tuning")
    return {
        "preferred_quality": report.get("preferred_quality"),
        "warn_policy": report.get("warn_policy"),
        "retrieval_tuning": tuning if isinstance(tuning, dict) else {},
        "modality": modality,
        "candidate_chunks": candidate_chunks,
        "scores": scores,
        "selected": selected,
        "top_chunk": top_chunk,
    }


def _selected_chunk_payload(item: dict[str, object]) -> dict[str, object]:
    source_url = _safe_string(item.get("source_name"))
    return {
        "doc_id": _safe_string(item.get("document_id")),
        "chunk_id": _safe_string(item.get("chunk_id")),
        "page_number": _safe_int(item.get("page_number")),
        "score": _safe_int(item.get("keyword_overlap")),
        "source_url": source_url,
        "modality": _infer_modality_from_source(source_url),
    }


def _infer_modality_from_source(source_url: str | None) -> str:
    path = Path(str(source_url or "").strip().lower())
    suffix = path.suffix
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    if suffix in _AUDIO_EXTENSIONS:
        return "audio"
    return "text"


def _summarize_modality(modalities: list[str]) -> str:
    if not modalities:
        return "text"
    unique: list[str] = []
    for item in modalities:
        if item not in unique:
            unique.append(item)
    if len(unique) == 1:
        return unique[0]
    return "mixed"


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            output.append(item)
    return output


def _safe_string(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    return parsed


def _safe_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed


__all__ = ["build_retrieval_explain_metadata"]
