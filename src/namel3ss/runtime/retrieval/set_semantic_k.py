from __future__ import annotations

from namel3ss.retrieval.tuning import SET_SEMANTIC_K, normalize_retrieval_k
from namel3ss.runtime.retrieval.tuning_state import write_tuning_value


def set_semantic_k(state: dict, value: object) -> int:
    normalized = normalize_retrieval_k(value, flow_name=SET_SEMANTIC_K)
    write_tuning_value(state, field="semantic_k", value=normalized)
    return normalized


__all__ = ["set_semantic_k"]
