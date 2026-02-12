from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.trace.trace_envelope_schema import (
    REQUIRED_TRACE_ENVELOPE_FIELDS,
    TRACE_ENVELOPE_SCHEMA_VERSION,
    empty_trace_envelope,
)


def build_trace_envelope(
    *,
    run_id: str | None,
    steps: Sequence[Mapping[str, object]] | None,
    sources_used: Sequence[Mapping[str, object] | str] | None,
    retrieval_stats: Mapping[str, object] | None,
    rationale: str | None,
    payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    step_ids = _step_ids(steps)
    normalized_sources = _normalize_sources(sources_used)
    normalized_stats = _normalize_stats(retrieval_stats)
    trace_payload = _normalize_payload(payload)
    resolved_run_id = _run_id(run_id, trace_payload=trace_payload, step_ids=step_ids)

    hashes = {
        "sources_hash": _sha256(canonical_json_dumps(normalized_sources, pretty=False, drop_run_keys=False)),
        "steps_hash": _sha256(canonical_json_dumps(step_ids, pretty=False, drop_run_keys=False)),
        "trace_hash": _sha256(canonical_json_dumps(trace_payload, pretty=False, drop_run_keys=False)),
    }
    envelope = {
        "hashes": hashes,
        "rationale": _text(rationale) or "No rationale provided.",
        "retrieval_stats": normalized_stats,
        "run_id": resolved_run_id,
        "sources_used": normalized_sources,
        "step_ids": step_ids,
        "trace_schema_version": TRACE_ENVELOPE_SCHEMA_VERSION,
    }
    if not _is_complete_envelope(envelope):
        return empty_trace_envelope()
    return envelope


def _is_complete_envelope(value: Mapping[str, object]) -> bool:
    return all(field in value for field in REQUIRED_TRACE_ENVELOPE_FIELDS)


def _normalize_payload(value: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=str)}


def _run_id(run_id: str | None, *, trace_payload: Mapping[str, object], step_ids: list[str]) -> str:
    text = _text(run_id)
    if text:
        return text
    digest = _sha256(
        canonical_json_dumps(
            {"payload": trace_payload, "step_ids": step_ids},
            pretty=False,
            drop_run_keys=False,
        )
    )
    return f"run_{digest[:16]}"


def _step_ids(steps: Sequence[Mapping[str, object]] | None) -> list[str]:
    values = list(steps or [])
    resolved: list[str] = []
    for index, step in enumerate(values, start=1):
        explicit = _text(step.get("id")) if isinstance(step, Mapping) else ""
        if explicit:
            resolved.append(explicit)
            continue
        normalized = {str(key): step[key] for key in sorted(step.keys(), key=str)} if isinstance(step, Mapping) else {}
        digest = _sha256(canonical_json_dumps(normalized, pretty=False, drop_run_keys=False))
        resolved.append(f"step_{index}_{digest[:8]}")
    return resolved


def _normalize_sources(value: Sequence[Mapping[str, object] | str] | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in value or ():
        if isinstance(item, Mapping):
            source_id = _text(item.get("source_id")) or _text(item.get("document_id")) or _text(item.get("id"))
            title = _text(item.get("title")) or source_id
            page_number = _int_value(item.get("page_number"))
            rows.append(
                {
                    "page_number": page_number,
                    "source_id": source_id,
                    "title": title,
                }
            )
            continue
        text = _text(item)
        if text:
            rows.append({"page_number": 0, "source_id": text, "title": text})
    rows.sort(key=lambda row: (str(row["source_id"]), int(row["page_number"]), str(row["title"])))
    return rows


def _normalize_stats(value: Mapping[str, object] | None) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {"candidates_considered": 0, "candidates_selected": 0}
    return {
        "candidates_considered": _int_value(value.get("candidates_considered")),
        "candidates_selected": _int_value(value.get("candidates_selected")),
    }


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value >= 0 else 0
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        return parsed if parsed >= 0 else 0
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = ["build_trace_envelope"]
