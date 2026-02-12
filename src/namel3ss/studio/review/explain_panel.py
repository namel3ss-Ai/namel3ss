from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.runtime.trace.trace_builder import build_trace_envelope
from namel3ss.runtime.trace.trace_envelope_schema import TRACE_ENVELOPE_MISSING_ERROR_CODE


def build_explain_panel_payload(trace_payload: Mapping[str, object] | None) -> dict[str, object]:
    payload = _mapping(trace_payload)
    envelope_value = payload.get("trace_envelope")
    envelope = _build_envelope_from_payload(payload, envelope_value)
    result = {
        "trace_envelope": envelope,
        "trace_schema_version": envelope.get("trace_schema_version"),
    }
    if not _mapping(trace_payload).get("trace_envelope"):
        result["error_code"] = TRACE_ENVELOPE_MISSING_ERROR_CODE
    return result


def _build_envelope_from_payload(
    payload: Mapping[str, object],
    envelope_value: object,
) -> dict[str, object]:
    if isinstance(envelope_value, Mapping):
        return {
            "hashes": _mapping(envelope_value.get("hashes")),
            "rationale": _text(envelope_value.get("rationale")) or "No rationale provided.",
            "retrieval_stats": _mapping(envelope_value.get("retrieval_stats")),
            "run_id": _text(envelope_value.get("run_id")) or "run_empty",
            "sources_used": _list_of_maps(envelope_value.get("sources_used")),
            "step_ids": _list_of_text(envelope_value.get("step_ids")),
            "trace_schema_version": _text(envelope_value.get("trace_schema_version")) or "trace_envelope@1",
        }
    return build_trace_envelope(
        run_id=_text(payload.get("run_id")),
        steps=_list_of_maps(payload.get("steps")),
        sources_used=_sources(payload.get("sources_used")),
        retrieval_stats=_mapping(payload.get("retrieval_stats")),
        rationale=_text(payload.get("rationale")),
        payload=payload,
    )


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=str)}


def _list_of_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append({str(key): item[key] for key in sorted(item.keys(), key=str)})
    return rows


def _list_of_text(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    rows: list[str] = []
    for item in value:
        text = _text(item)
        if text:
            rows.append(text)
    return rows


def _sources(value: object) -> list[dict[str, object] | str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    rows: list[dict[str, object] | str] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append({str(key): item[key] for key in sorted(item.keys(), key=str)})
        else:
            text = _text(item)
            if text:
                rows.append(text)
    return rows


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


__all__ = ["build_explain_panel_payload"]
