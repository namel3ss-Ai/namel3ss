from __future__ import annotations

from dataclasses import dataclass


def normalize_retrieval_mode(value: str | None) -> str:
    if value == "quick-only":
        return "quick"
    if value == "deep-only":
        return "deep"
    return "auto"


@dataclass
class _ExplainCandidate:
    chunk_id: str
    ingestion_phase: str
    keyword_overlap: int
    page_number: int
    chunk_index: int
    vector_score: float | None
    decision: str | None
    reason: str | None
    rank_key: tuple | None
    order_index: int
    quality: str | None


class RetrievalExplainBuilder:
    def __init__(self, query: str, tier_request: str | None, limit: int | None) -> None:
        self.query = query
        self.tier_request = tier_request
        self.limit = limit
        self._candidates: list[_ExplainCandidate] = []

    def add_blocked(
        self,
        *,
        chunk_id: str,
        ingestion_phase: str,
        keyword_overlap: int,
        page_number: int,
        chunk_index: int,
        order_index: int,
        vector_score: float | None = None,
    ) -> None:
        self._candidates.append(
            _ExplainCandidate(
                chunk_id=chunk_id,
                ingestion_phase=ingestion_phase,
                keyword_overlap=keyword_overlap,
                page_number=page_number,
                chunk_index=chunk_index,
                vector_score=vector_score,
                decision="excluded",
                reason="blocked",
                rank_key=None,
                order_index=order_index,
                quality=None,
            )
        )

    def add_filtered(
        self,
        *,
        chunk_id: str,
        ingestion_phase: str,
        keyword_overlap: int,
        page_number: int,
        chunk_index: int,
        order_index: int,
        quality: str,
        vector_score: float | None = None,
    ) -> None:
        self._candidates.append(
            _ExplainCandidate(
                chunk_id=chunk_id,
                ingestion_phase=ingestion_phase,
                keyword_overlap=keyword_overlap,
                page_number=page_number,
                chunk_index=chunk_index,
                vector_score=vector_score,
                decision="excluded",
                reason="filtered",
                rank_key=None,
                order_index=order_index,
                quality=quality,
            )
        )

    def add_candidate(
        self,
        *,
        chunk_id: str,
        ingestion_phase: str,
        keyword_overlap: int,
        page_number: int,
        chunk_index: int,
        order_index: int,
        quality: str,
        rank_key: tuple,
        vector_score: float | None = None,
    ) -> None:
        self._candidates.append(
            _ExplainCandidate(
                chunk_id=chunk_id,
                ingestion_phase=ingestion_phase,
                keyword_overlap=keyword_overlap,
                page_number=page_number,
                chunk_index=chunk_index,
                vector_score=vector_score,
                decision=None,
                reason=None,
                rank_key=rank_key,
                order_index=order_index,
                quality=quality,
            )
        )

    def finalize(
        self,
        *,
        selected: list[dict],
        selection_candidates: list[dict],
        chosen_quality: str | None,
        warn_allowed: bool,
        embedding: dict | None = None,
        ordering: str | None = None,
    ) -> dict:
        selected_ids = _chunk_ids(selected)
        selection_ids = _chunk_ids(selection_candidates)
        for candidate in self._candidates:
            if candidate.decision is not None:
                continue
            if candidate.quality == "warn" and not warn_allowed:
                candidate.decision = "excluded"
                candidate.reason = "quality_policy"
                continue
            if chosen_quality == "pass" and candidate.quality == "warn":
                candidate.decision = "excluded"
                candidate.reason = "quality_policy"
                continue
            if candidate.chunk_id in selected_ids:
                candidate.decision = "selected"
                candidate.reason = "top_k"
                continue
            if candidate.chunk_id in selection_ids:
                candidate.decision = "excluded"
                candidate.reason = "lower_rank"
                continue
            if candidate.quality == "warn" and not warn_allowed:
                candidate.decision = "excluded"
                candidate.reason = "quality_policy"
            else:
                candidate.decision = "excluded"
                candidate.reason = "tier"
        ordered = _ordered_candidates(self._candidates)
        output = [_candidate_payload(item) for item in ordered]
        embedding_payload = embedding if isinstance(embedding, dict) else _default_embedding_payload()
        return {
            "query": self.query,
            "retrieval_mode": normalize_retrieval_mode(self.tier_request),
            "candidate_count": len(output),
            "candidates": output,
            "final_selection": [item.get("chunk_id") for item in selected if isinstance(item, dict)],
            "ordering": ordering or "ingestion_phase, keyword_overlap, page_number, chunk_index",
            "embedding": embedding_payload,
        }


def _ordered_candidates(candidates: list[_ExplainCandidate]) -> list[_ExplainCandidate]:
    ranked = [item for item in candidates if item.rank_key is not None]
    unranked = [item for item in candidates if item.rank_key is None]
    ranked.sort(key=lambda item: item.rank_key)
    unranked.sort(key=lambda item: item.order_index)
    return ranked + unranked


def _candidate_payload(item: _ExplainCandidate) -> dict:
    return {
        "chunk_id": item.chunk_id,
        "ingestion_phase": item.ingestion_phase,
        "keyword_overlap": item.keyword_overlap,
        "page_number": item.page_number,
        "chunk_index": item.chunk_index,
        "vector_score": item.vector_score,
        "decision": item.decision or "excluded",
        "reason": item.reason or "unknown",
    }


def _chunk_ids(entries: list[dict]) -> set[str]:
    ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = entry.get("chunk_id")
        if value is None:
            continue
        ids.add(str(value))
    return ids


def _default_embedding_payload() -> dict:
    return {"enabled": False, "model_id": None, "candidate_count": 0, "candidates": []}


__all__ = ["RetrievalExplainBuilder", "normalize_retrieval_mode"]
