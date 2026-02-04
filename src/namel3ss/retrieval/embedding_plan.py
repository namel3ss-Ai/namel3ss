from __future__ import annotations

from dataclasses import dataclass

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.hash import hash_chunk
from namel3ss.runtime.embeddings.service import (
    embed_text,
    embedding_enabled,
    resolve_embedding_model,
    vector_is_zero,
    vector_similarity,
)
from namel3ss.runtime.embeddings.store import EmbeddingRecord, get_embedding_store


@dataclass(frozen=True)
class EmbeddingPlan:
    enabled: bool
    model_id: str | None
    candidate_ids: frozenset[str]
    scores: dict[str, float]
    candidates: list[dict]

    def score_for(self, chunk_id: str) -> float | None:
        return self.scores.get(chunk_id)

    def is_candidate(self, chunk_id: str) -> bool:
        return chunk_id in self.candidate_ids

    def explain_payload(self) -> dict:
        return {
            "enabled": self.enabled,
            "model_id": self.model_id,
            "candidate_count": len(self.candidates),
            "candidates": list(self.candidates),
        }


def build_embedding_plan(
    entries: list[dict],
    *,
    query_text: str,
    config: AppConfig | None,
    project_root: str | None,
    app_path: str | None,
    capabilities: tuple[str, ...] | list[str] | None,
) -> EmbeddingPlan:
    if not embedding_enabled(capabilities):
        return EmbeddingPlan(False, None, frozenset(), {}, [])
    cfg = config or load_config(
        app_path=app_path if isinstance(app_path, str) else None,
        root=project_root if isinstance(project_root, str) else None,
    )
    model = resolve_embedding_model(cfg)
    store = get_embedding_store(cfg, project_root=project_root, app_path=app_path)
    if not isinstance(query_text, str) or not query_text.strip():
        return EmbeddingPlan(True, model.model_id, frozenset(), {}, [])
    query_vector = embed_text(query_text, model)
    if vector_is_zero(query_vector):
        return EmbeddingPlan(True, model.model_id, frozenset(), {}, [])
    lookup, hashes = _entry_hashes(entries)
    records = store.get_records(model_id=model.model_id, chunk_hashes=hashes)
    scores = _score_records(records, lookup, query_vector, model.precision, model.dims)
    candidates = _select_candidates(scores, model.candidate_limit)
    candidate_ids = frozenset(item["chunk_id"] for item in candidates)
    return EmbeddingPlan(
        True,
        model.model_id,
        candidate_ids,
        scores,
        candidates,
    )


def _entry_hashes(entries: list[dict]) -> tuple[dict[str, str], list[str]]:
    lookup: dict[str, str] = {}
    hashes: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        chunk_hash = _chunk_hash_for_entry(entry)
        if not chunk_hash:
            continue
        chunk_id = _chunk_id_for_entry(entry)
        lookup[chunk_hash] = chunk_id
        hashes.append(chunk_hash)
    return lookup, hashes


def _chunk_id_for_entry(entry: dict) -> str:
    value = entry.get("chunk_id")
    if isinstance(value, str) and value:
        return value
    upload_id = entry.get("upload_id")
    chunk_index = entry.get("chunk_index")
    if isinstance(upload_id, str) and isinstance(chunk_index, int):
        return f"{upload_id}:{chunk_index}"
    return ""


def _chunk_hash_for_entry(entry: dict) -> str | None:
    value = entry.get("chunk_hash")
    if isinstance(value, str) and value:
        return value
    document_id = entry.get("document_id")
    page_number = entry.get("page_number")
    chunk_index = entry.get("chunk_index")
    text = entry.get("text")
    if not isinstance(document_id, str):
        return None
    if not isinstance(page_number, int) or not isinstance(chunk_index, int):
        return None
    return hash_chunk(
        document_id=document_id,
        page_number=page_number,
        chunk_index=chunk_index,
        text=str(text or ""),
    )


def _score_records(
    records: dict[str, EmbeddingRecord],
    lookup: dict[str, str],
    query_vector: list[float],
    precision: int,
    dims: int,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for chunk_hash, record in records.items():
        if record.status != "ok":
            continue
        if record.vector is None:
            continue
        if record.dims != dims:
            raise Namel3ssError(_dims_mismatch_message(record.dims, dims))
        chunk_id = lookup.get(chunk_hash)
        if not chunk_id:
            continue
        score = vector_similarity(query_vector, record.vector, precision=precision)
        scores[chunk_id] = score
    return scores


def _select_candidates(scores: dict[str, float], limit: int) -> list[dict]:
    if not scores or limit <= 0:
        return []
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    output: list[dict] = []
    for chunk_id, score in ordered[:limit]:
        output.append({"chunk_id": chunk_id, "score": score})
    return output


def _dims_mismatch_message(found: int, expected: int) -> str:
    return build_guidance_message(
        what=f"Embedding vector dims mismatch (expected {expected}, found {found}).",
        why="Embeddings must be generated with a consistent model configuration.",
        fix="Ensure the embedding model config matches stored vectors.",
        example='[embedding]\nmodel = "hash"\nversion = "v1"\ndims = 64',
    )


__all__ = ["EmbeddingPlan", "build_embedding_plan"]
