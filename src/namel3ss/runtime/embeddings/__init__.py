from __future__ import annotations

from namel3ss.runtime.embeddings.service import (
    EmbeddingModel,
    embed_text,
    embedding_enabled,
    resolve_embedding_model,
    vector_is_zero,
    vector_similarity,
)
from namel3ss.runtime.embeddings.store import EmbeddingRecord, get_embedding_store


__all__ = [
    "EmbeddingModel",
    "EmbeddingRecord",
    "embed_text",
    "embedding_enabled",
    "get_embedding_store",
    "resolve_embedding_model",
    "vector_is_zero",
    "vector_similarity",
]
