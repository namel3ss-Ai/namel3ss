from __future__ import annotations

from pathlib import Path
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.observability.context import ObservabilityContext
from namel3ss.observability.log_store import read_logs
from namel3ss.observability.metrics_store import TIMING_BUCKETS, read_metrics
from namel3ss.observability.scrub import scrub_payload
from namel3ss.observability.trace_store import read_spans


OBSERVABILITY_SCHEMA_VERSION = 1


def build_observability_payload(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    secret_values: Iterable[str] | None = None,
    observability: ObservabilityContext | None = None,
) -> dict:
    secrets = list(secret_values or [])
    scrub = lambda value: scrub_payload(value, secret_values=secrets, project_root=project_root, app_path=app_path)
    logs = _load_logs(project_root, app_path, observability)
    spans = _load_spans(project_root, app_path, observability)
    metrics = _load_metrics(project_root, app_path, observability)

    scrubbed_logs = [scrub(entry) for entry in logs]
    scrubbed_spans = [scrub(entry) for entry in spans]
    scrubbed_metrics = scrub(metrics)

    normalized_logs = _normalize_logs(scrubbed_logs)
    normalized_spans = _normalize_spans(scrubbed_spans)
    normalized_metrics = _normalize_metrics(scrubbed_metrics)

    return {
        "schema_version": OBSERVABILITY_SCHEMA_VERSION,
        "logs": normalized_logs,
        "spans": normalized_spans,
        "metrics": normalized_metrics,
    }


def _load_logs(
    project_root: str | Path | None,
    app_path: str | Path | None,
    observability: ObservabilityContext | None,
) -> list[dict]:
    if observability is not None:
        return [entry for entry in observability.logs.snapshot() if isinstance(entry, dict)]
    return [entry for entry in read_logs(project_root, app_path) if isinstance(entry, dict)]


def _load_spans(
    project_root: str | Path | None,
    app_path: str | Path | None,
    observability: ObservabilityContext | None,
) -> list[dict]:
    if observability is not None:
        return [entry for entry in observability.traces.snapshot() if isinstance(entry, dict)]
    return [entry for entry in read_spans(project_root, app_path) if isinstance(entry, dict)]


def _load_metrics(
    project_root: str | Path | None,
    app_path: str | Path | None,
    observability: ObservabilityContext | None,
) -> dict:
    if observability is not None:
        return observability.metrics.snapshot()
    return read_metrics(project_root, app_path)


def _normalize_logs(entries: list[object]) -> list[dict]:
    normalized: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        level = str(entry.get("level", "info")).lower()
        name = entry.get("name") or "log.message"
        kind = entry.get("kind") or level
        message = entry.get("message")
        fields = _normalize_fields(entry.get("fields"))
        if message not in (None, ""):
            fields = dict(fields)
            fields.setdefault("message", _primitive_value(message))
        event = {
            "id": str(entry.get("id", "")),
            "name": str(name),
            "kind": str(kind),
            "fields": fields,
        }
        span_id = entry.get("span_id")
        if span_id:
            event["span_id"] = str(span_id)
        normalized.append(event)
    normalized.sort(key=lambda item: item.get("id", ""))
    return normalized


def _normalize_spans(entries: list[object]) -> list[dict]:
    normalized: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details")
        details_payload = _normalize_fields(details) if isinstance(details, dict) else {}
        span = {
            "id": str(entry.get("id", "")),
            "name": str(entry.get("name", "")),
            "kind": str(entry.get("kind", "")),
            "status": str(entry.get("status", "")),
            "start_step": _coerce_int(entry.get("start_step")),
            "end_step": _coerce_int(entry.get("end_step")),
            "duration_steps": _coerce_int(entry.get("duration_steps")),
            "details": details_payload,
        }
        parent_id = entry.get("parent_id")
        if parent_id:
            span["parent_id"] = str(parent_id)
        normalized.append(span)
    normalized.sort(key=lambda item: item.get("id", ""))
    return normalized


def _normalize_metrics(payload: object) -> dict:
    data = payload if isinstance(payload, dict) else {}
    counters = data.get("counters") if isinstance(data.get("counters"), list) else []
    timings = data.get("timings") if isinstance(data.get("timings"), list) else []
    normalized_counters = [_normalize_counter(entry) for entry in counters if isinstance(entry, dict)]
    normalized_timings = [_normalize_timing(entry) for entry in timings if isinstance(entry, dict)]
    normalized_counters.sort(key=_metric_sort_key)
    normalized_timings.sort(key=_metric_sort_key)
    return {"counters": normalized_counters, "timings": normalized_timings}


def _normalize_counter(entry: dict) -> dict:
    name = str(entry.get("name", ""))
    labels = _normalize_fields(entry.get("labels"))
    return {"name": name, "labels": labels, "value": _coerce_number(entry.get("value"))}


def _normalize_timing(entry: dict) -> dict:
    name = str(entry.get("name", ""))
    labels = _normalize_fields(entry.get("labels"))
    buckets = _normalize_buckets(entry.get("buckets"))
    return {
        "name": name,
        "labels": labels,
        "unit": "steps",
        "count": _coerce_int(entry.get("count")),
        "total_steps": _coerce_int(entry.get("total_steps")),
        "min_steps": _coerce_optional_int(entry.get("min_steps")),
        "max_steps": _coerce_optional_int(entry.get("max_steps")),
        "last_steps": _coerce_int(entry.get("last_steps")),
        "buckets": buckets,
    }


def _normalize_fields(fields: object) -> dict:
    if not isinstance(fields, dict):
        return {}
    normalized: dict[str, object] = {}
    for key in sorted(fields.keys(), key=lambda item: str(item)):
        normalized[str(key)] = _primitive_value(fields.get(key))
    return normalized


def _normalize_buckets(raw: object) -> list[dict]:
    counts: dict[tuple[str, int], int] = {}
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if "le" in entry:
                bound = _coerce_int(entry.get("le"))
                counts[("le", bound)] = _coerce_int(entry.get("count"))
            elif "gt" in entry:
                bound = _coerce_int(entry.get("gt"))
                counts[("gt", bound)] = _coerce_int(entry.get("count"))
    buckets = [{"le": bound, "count": counts.get(("le", bound), 0)} for bound in TIMING_BUCKETS]
    buckets.append({"gt": TIMING_BUCKETS[-1], "count": counts.get(("gt", TIMING_BUCKETS[-1]), 0)})
    return buckets


def _metric_sort_key(entry: dict) -> tuple:
    name = str(entry.get("name", ""))
    labels = entry.get("labels", {})
    labels = labels if isinstance(labels, dict) else {}
    label_key = tuple((str(key), str(labels.get(key))) for key in sorted(labels.keys(), key=lambda item: str(item)))
    return (name, label_key)


def _primitive_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return canonical_json_dumps(value, pretty=False, drop_run_keys=False)
    except Exception:
        return str(value)


def _coerce_int(value: object) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _coerce_number(value: object) -> int | float:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    try:
        as_float = float(value)
    except Exception:
        return 0
    if as_float.is_integer():
        return int(as_float)
    return as_float


__all__ = ["OBSERVABILITY_SCHEMA_VERSION", "build_observability_payload"]
