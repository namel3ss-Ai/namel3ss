from __future__ import annotations

from namel3ss.rag.contracts.retrieval_config_model import normalize_retrieval_config_model
from namel3ss.rag.contracts.value_norms import map_value, merge_extensions, text_value, unknown_extensions
from namel3ss.rag.determinism.id_policy import build_run_determinism_fingerprint
from namel3ss.rag.determinism.json_policy import canonical_contract_copy


TRACE_SCHEMA_VERSION = "rag.trace@1"


def build_trace_model(
    *,
    input_payload: object,
    retrieval_config: object,
    retrieved_chunk_ids: object,
    events: object,
    run_id: str = "",
    schema_version: str = TRACE_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    input_payload_value = map_value(input_payload)
    retrieval_config_value = normalize_retrieval_config_model(retrieval_config)
    chunk_ids = _normalize_chunk_ids(retrieved_chunk_ids)
    fingerprint = build_run_determinism_fingerprint(
        input_payload=input_payload_value,
        retrieval_config=retrieval_config_value,
        retrieved_chunk_ids=chunk_ids,
    )
    return {
        "schema_version": text_value(schema_version, default=TRACE_SCHEMA_VERSION) or TRACE_SCHEMA_VERSION,
        "run_id": text_value(run_id),
        "run_determinism_fingerprint": fingerprint,
        "input_payload": canonical_contract_copy(input_payload_value),
        "retrieval_config": canonical_contract_copy(retrieval_config_value),
        "retrieved_chunk_ids": chunk_ids,
        "events": _normalize_events(events),
        "extensions": merge_extensions(extensions),
    }


def normalize_trace_model(value: object) -> dict[str, object]:
    data = map_value(value)
    provided_extensions = map_value(data.get("extensions"))
    retrieval_config = normalize_retrieval_config_model(data.get("retrieval_config"))
    input_payload = map_value(data.get("input_payload"))
    chunk_ids = _normalize_chunk_ids(data.get("retrieved_chunk_ids"))
    fingerprint = text_value(data.get("run_determinism_fingerprint")) or build_run_determinism_fingerprint(
        input_payload=input_payload,
        retrieval_config=retrieval_config,
        retrieved_chunk_ids=chunk_ids,
    )
    extensions = merge_extensions(
        provided_extensions,
        unknown_extensions(data, known_keys=_KNOWN_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=TRACE_SCHEMA_VERSION) or TRACE_SCHEMA_VERSION,
        "run_id": text_value(data.get("run_id")),
        "run_determinism_fingerprint": fingerprint,
        "input_payload": canonical_contract_copy(input_payload),
        "retrieval_config": canonical_contract_copy(retrieval_config),
        "retrieved_chunk_ids": chunk_ids,
        "events": _normalize_events(data.get("events")),
        "extensions": extensions,
    }


def _normalize_chunk_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    for item in value:
        token = text_value(item)
        if not token:
            continue
        rows.append(token)
    return rows


def _normalize_events(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        rows.append(canonical_contract_copy(map_value(item)))
    return rows


_KNOWN_FIELDS = {
    "schema_version",
    "run_id",
    "run_determinism_fingerprint",
    "input_payload",
    "retrieval_config",
    "retrieved_chunk_ids",
    "events",
    "extensions",
}


__all__ = [
    "TRACE_SCHEMA_VERSION",
    "build_trace_model",
    "normalize_trace_model",
]
