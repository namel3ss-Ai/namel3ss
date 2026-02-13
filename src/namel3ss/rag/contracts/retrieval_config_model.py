from __future__ import annotations

from namel3ss.rag.contracts.value_norms import (
    int_value,
    map_value,
    merge_extensions,
    sorted_string_list,
    string_list,
    text_value,
    unknown_extensions,
)
from namel3ss.rag.determinism.order_policy import normalize_score


RETRIEVAL_CONFIG_SCHEMA_VERSION = "rag.retrieval_config@1"


def build_retrieval_config_model(
    *,
    top_k: int = 8,
    hybrid_weights: object = None,
    rerank_model_id: str = "",
    filters: object = None,
    scope: object = None,
    parser_version: str = "",
    chunking_version: str = "",
    schema_version: str = RETRIEVAL_CONFIG_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": text_value(schema_version, default=RETRIEVAL_CONFIG_SCHEMA_VERSION) or RETRIEVAL_CONFIG_SCHEMA_VERSION,
        "top_k": int_value(top_k, minimum=1, default=8),
        "hybrid_weights": _normalize_hybrid_weights(hybrid_weights),
        "rerank_model_id": text_value(rerank_model_id),
        "filters": _normalize_filters(filters),
        "scope": _normalize_scope(scope),
        "parser_version": text_value(parser_version),
        "chunking_version": text_value(chunking_version),
        "extensions": merge_extensions(extensions),
    }


def normalize_retrieval_config_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=RETRIEVAL_CONFIG_SCHEMA_VERSION) or RETRIEVAL_CONFIG_SCHEMA_VERSION,
        "top_k": int_value(data.get("top_k"), minimum=1, default=8),
        "hybrid_weights": _normalize_hybrid_weights(data.get("hybrid_weights")),
        "rerank_model_id": text_value(data.get("rerank_model_id")),
        "filters": _normalize_filters(data.get("filters")),
        "scope": _normalize_scope(data.get("scope")),
        "parser_version": text_value(data.get("parser_version")),
        "chunking_version": text_value(data.get("chunking_version")),
        "extensions": extensions,
    }


def _normalize_hybrid_weights(value: object) -> dict[str, float]:
    data = map_value(value)
    semantic = normalize_score(data.get("semantic_weight", 0.5))
    keyword = normalize_score(data.get("keyword_weight", 0.5))
    return {
        "keyword_weight": float(keyword),
        "semantic_weight": float(semantic),
    }


def _normalize_filters(value: object) -> dict[str, object]:
    data = map_value(value)
    normalized: dict[str, object] = {}
    for key in data.keys():
        entry = data[key]
        if isinstance(entry, list):
            normalized[key] = sorted_string_list(entry)
        elif isinstance(entry, bool):
            normalized[key] = bool(entry)
        elif isinstance(entry, (int, float)):
            normalized[key] = float(entry)
        else:
            normalized[key] = text_value(entry)
    return normalized


def _normalize_scope(value: object) -> dict[str, object]:
    data = map_value(value)
    return {
        "collections": sorted_string_list(data.get("collections")),
        "documents": sorted_string_list(data.get("documents")),
        "tenant_id": text_value(data.get("tenant_id")),
    }


_KNOWN_FIELDS = {
    "schema_version",
    "top_k",
    "hybrid_weights",
    "rerank_model_id",
    "filters",
    "scope",
    "parser_version",
    "chunking_version",
    "extensions",
}


__all__ = [
    "RETRIEVAL_CONFIG_SCHEMA_VERSION",
    "build_retrieval_config_model",
    "normalize_retrieval_config_model",
]
