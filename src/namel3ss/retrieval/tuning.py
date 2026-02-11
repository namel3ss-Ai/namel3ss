from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal


SET_SEMANTIC_K = "set_semantic_k"
SET_LEXICAL_K = "set_lexical_k"
SET_FINAL_TOP_K = "set_final_top_k"
SET_SEMANTIC_WEIGHT = "set_semantic_weight"

RETRIEVAL_TUNING_FLOWS: tuple[str, ...] = (
    SET_SEMANTIC_K,
    SET_LEXICAL_K,
    SET_FINAL_TOP_K,
    SET_SEMANTIC_WEIGHT,
)

RETRIEVAL_TUNING_FLOW_TO_FIELD: dict[str, str] = {
    SET_SEMANTIC_K: "semantic_k",
    SET_LEXICAL_K: "lexical_k",
    SET_FINAL_TOP_K: "final_top_k",
    SET_SEMANTIC_WEIGHT: "semantic_weight",
}

RETRIEVAL_TUNING_FIELD_ORDER: tuple[str, ...] = (
    "semantic_k",
    "lexical_k",
    "final_top_k",
    "semantic_weight",
)

DEFAULT_SEMANTIC_WEIGHT = 0.5
RETRIEVAL_STATE_KEY = "retrieval"
RETRIEVAL_TUNING_STATE_KEY = "tuning"


@dataclass(frozen=True)
class RetrievalTuning:
    semantic_k: int | None
    lexical_k: int | None
    final_top_k: int | None
    semantic_weight: float
    explicit: bool

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "semantic_k": self.semantic_k,
            "lexical_k": self.lexical_k,
            "final_top_k": self.final_top_k,
            "semantic_weight": round(float(self.semantic_weight), 4),
            "explicit": self.explicit,
        }
        return payload


def is_retrieval_tuning_flow(name: str) -> bool:
    return name in set(RETRIEVAL_TUNING_FLOWS)


def retrieval_tuning_field_for_flow(name: str) -> str | None:
    return RETRIEVAL_TUNING_FLOW_TO_FIELD.get(name)


def normalize_retrieval_k(value: object, *, flow_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{flow_name} expects an integer k >= 0.")
    normalized: int
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, Decimal) and value == value.to_integral_value():
        normalized = int(value)
    else:
        raise ValueError(f"{flow_name} expects an integer k >= 0.")
    if normalized < 0:
        raise ValueError(f"{flow_name} expects k >= 0.")
    return normalized


def normalize_retrieval_weight(value: object, *, flow_name: str = SET_SEMANTIC_WEIGHT) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{flow_name} expects a numeric weight between 0 and 1.")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{flow_name} expects weight in [0, 1].")
    return round(number, 4)


def read_tuning_from_state(state: Mapping[str, object] | None) -> RetrievalTuning:
    retrieval = state.get(RETRIEVAL_STATE_KEY) if isinstance(state, Mapping) else None
    tuning = retrieval.get(RETRIEVAL_TUNING_STATE_KEY) if isinstance(retrieval, Mapping) else None
    if not isinstance(tuning, Mapping):
        return RetrievalTuning(
            semantic_k=None,
            lexical_k=None,
            final_top_k=None,
            semantic_weight=DEFAULT_SEMANTIC_WEIGHT,
            explicit=False,
        )
    seen_fields = set(tuning.keys()) & set(RETRIEVAL_TUNING_FIELD_ORDER)
    explicit = bool(seen_fields)
    semantic_k = _read_optional_k(tuning, "semantic_k", flow_name=SET_SEMANTIC_K)
    lexical_k = _read_optional_k(tuning, "lexical_k", flow_name=SET_LEXICAL_K)
    final_top_k = _read_optional_k(tuning, "final_top_k", flow_name=SET_FINAL_TOP_K)
    if "semantic_weight" in tuning:
        semantic_weight = normalize_retrieval_weight(tuning.get("semantic_weight"), flow_name=SET_SEMANTIC_WEIGHT)
    else:
        semantic_weight = DEFAULT_SEMANTIC_WEIGHT
    return RetrievalTuning(
        semantic_k=semantic_k,
        lexical_k=lexical_k,
        final_top_k=final_top_k,
        semantic_weight=semantic_weight,
        explicit=explicit,
    )


def canonical_tuning_payload(values: Mapping[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field in RETRIEVAL_TUNING_FIELD_ORDER:
        if field not in values:
            continue
        value = values.get(field)
        if value is None:
            continue
        payload[field] = value
    return payload


def _read_optional_k(values: Mapping[str, object], field: str, *, flow_name: str) -> int | None:
    if field not in values:
        return None
    return normalize_retrieval_k(values.get(field), flow_name=flow_name)


__all__ = [
    "DEFAULT_SEMANTIC_WEIGHT",
    "RETRIEVAL_STATE_KEY",
    "RETRIEVAL_TUNING_FIELD_ORDER",
    "RETRIEVAL_TUNING_FLOW_TO_FIELD",
    "RETRIEVAL_TUNING_FLOWS",
    "RETRIEVAL_TUNING_STATE_KEY",
    "RetrievalTuning",
    "SET_FINAL_TOP_K",
    "SET_LEXICAL_K",
    "SET_SEMANTIC_K",
    "SET_SEMANTIC_WEIGHT",
    "canonical_tuning_payload",
    "is_retrieval_tuning_flow",
    "normalize_retrieval_k",
    "normalize_retrieval_weight",
    "read_tuning_from_state",
    "retrieval_tuning_field_for_flow",
]
