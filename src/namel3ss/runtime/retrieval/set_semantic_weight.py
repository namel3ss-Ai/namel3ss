from __future__ import annotations

from namel3ss.retrieval.tuning import SET_SEMANTIC_WEIGHT, normalize_retrieval_weight
from namel3ss.runtime.retrieval.tuning_state import write_tuning_value


def set_semantic_weight(state: dict, value: object) -> float:
    normalized = normalize_retrieval_weight(value, flow_name=SET_SEMANTIC_WEIGHT)
    write_tuning_value(state, field="semantic_weight", value=normalized)
    return normalized


__all__ = ["set_semantic_weight"]
