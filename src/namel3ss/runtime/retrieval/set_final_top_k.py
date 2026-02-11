from __future__ import annotations

from namel3ss.retrieval.tuning import SET_FINAL_TOP_K, normalize_retrieval_k
from namel3ss.runtime.retrieval.tuning_state import write_tuning_value


def set_final_top_k(state: dict, value: object) -> int:
    normalized = normalize_retrieval_k(value, flow_name=SET_FINAL_TOP_K)
    write_tuning_value(state, field="final_top_k", value=normalized)
    return normalized


__all__ = ["set_final_top_k"]
