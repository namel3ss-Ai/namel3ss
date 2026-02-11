from __future__ import annotations

from collections.abc import Mapping

from namel3ss.retrieval.tuning import (
    RETRIEVAL_STATE_KEY,
    RETRIEVAL_TUNING_FIELD_ORDER,
    RETRIEVAL_TUNING_STATE_KEY,
    canonical_tuning_payload,
)


def write_tuning_value(state: dict, *, field: str, value: object) -> None:
    retrieval = _ensure_retrieval_state(state)
    current = retrieval.get(RETRIEVAL_TUNING_STATE_KEY)
    existing = dict(current) if isinstance(current, Mapping) else {}
    if value is None:
        existing.pop(field, None)
    else:
        existing[field] = value
    payload = canonical_tuning_payload(existing)
    retrieval[RETRIEVAL_TUNING_STATE_KEY] = payload


def read_tuning_values(state: object) -> dict[str, object]:
    if not isinstance(state, Mapping):
        return {}
    retrieval = state.get(RETRIEVAL_STATE_KEY)
    if not isinstance(retrieval, Mapping):
        return {}
    tuning = retrieval.get(RETRIEVAL_TUNING_STATE_KEY)
    if not isinstance(tuning, Mapping):
        return {}
    payload: dict[str, object] = {}
    for field in RETRIEVAL_TUNING_FIELD_ORDER:
        if field in tuning:
            payload[field] = tuning.get(field)
    return payload


def _ensure_retrieval_state(state: dict) -> dict:
    retrieval = state.get(RETRIEVAL_STATE_KEY)
    if isinstance(retrieval, dict):
        return retrieval
    retrieval = {}
    state[RETRIEVAL_STATE_KEY] = retrieval
    return retrieval


__all__ = ["read_tuning_values", "write_tuning_value"]
