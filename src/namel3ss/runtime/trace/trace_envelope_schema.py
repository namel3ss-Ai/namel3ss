from __future__ import annotations

TRACE_ENVELOPE_SCHEMA_VERSION = "trace_envelope@1"
TRACE_ENVELOPE_MISSING_ERROR_CODE = "N3E_TRACE_ENVELOPE_MISSING"


REQUIRED_TRACE_ENVELOPE_FIELDS: tuple[str, ...] = (
    "hashes",
    "rationale",
    "retrieval_stats",
    "run_id",
    "sources_used",
    "step_ids",
    "trace_schema_version",
)


def empty_trace_envelope() -> dict[str, object]:
    return {
        "hashes": {"sources_hash": "", "steps_hash": "", "trace_hash": ""},
        "rationale": "No rationale provided.",
        "retrieval_stats": {"candidates_considered": 0, "candidates_selected": 0},
        "run_id": "run_empty",
        "sources_used": [],
        "step_ids": [],
        "trace_schema_version": TRACE_ENVELOPE_SCHEMA_VERSION,
    }


__all__ = [
    "REQUIRED_TRACE_ENVELOPE_FIELDS",
    "TRACE_ENVELOPE_MISSING_ERROR_CODE",
    "TRACE_ENVELOPE_SCHEMA_VERSION",
    "empty_trace_envelope",
]
