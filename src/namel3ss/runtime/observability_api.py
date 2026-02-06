from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.observability.enablement import observability_enabled
from namel3ss.observability.log_store import read_logs
from namel3ss.observability.metrics_store import read_metrics
from namel3ss.observability.scrub import scrub_payload
from namel3ss.observability.trace_store import read_spans
from namel3ss.observability.trace_runs import latest_trace_run_id, list_trace_runs, read_trace_entries
from namel3ss.secrets import collect_secret_values


def get_logs_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    if not observability_enabled():
        return {"ok": True, "count": 0, "logs": []}
    scrub = _scrubber(project_root, app_path)
    logs = [scrub(item) for item in read_logs(project_root, app_path)]
    logs = [item for item in logs if isinstance(item, dict)]
    return {"ok": True, "count": len(logs), "logs": logs}


def get_trace_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    if not observability_enabled():
        return {"ok": True, "count": 0, "spans": []}
    scrub = _scrubber(project_root, app_path)
    spans = [scrub(item) for item in read_spans(project_root, app_path)]
    spans = [item for item in spans if isinstance(item, dict)]
    return {"ok": True, "count": len(spans), "spans": spans}


def get_traces_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    return get_trace_payload(project_root, app_path)


def get_trace_runs_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    runs = list_trace_runs(project_root, app_path)
    return {"ok": True, "count": len(runs), "runs": runs}


def get_latest_trace_run_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    run_id = latest_trace_run_id(project_root, app_path)
    if not run_id:
        return {"ok": True, "run_id": None, "count": 0, "trace": []}
    return get_trace_run_payload(project_root, app_path, run_id)


def get_trace_run_payload(project_root: str | Path | None, app_path: str | Path | None, run_id: str) -> dict:
    cleaned_id = str(run_id or "").strip()
    if not cleaned_id:
        return {"ok": False, "error": "Run id is required.", "kind": "engine"}
    entries = read_trace_entries(project_root, app_path, cleaned_id)
    if not entries:
        return {"ok": False, "error": f'Trace run "{cleaned_id}" was not found.', "kind": "engine"}
    scrub = _scrubber(project_root, app_path)
    trace = [scrub(item) for item in entries]
    trace = [item for item in trace if isinstance(item, dict)]
    return {"ok": True, "run_id": cleaned_id, "count": len(trace), "trace": trace}


def get_metrics_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict:
    if not observability_enabled():
        return {"ok": True, "counters": [], "timings": []}
    scrub = _scrubber(project_root, app_path)
    metrics = read_metrics(project_root, app_path)
    cleaned = scrub(metrics)
    if not isinstance(cleaned, dict):
        cleaned = {"counters": [], "timings": []}
    cleaned.setdefault("counters", [])
    cleaned.setdefault("timings", [])
    cleaned["ok"] = True
    return cleaned


def _scrubber(project_root: str | Path | None, app_path: str | Path | None):
    config = None
    try:
        config = load_config(app_path=app_path, root=project_root)
    except Exception:
        config = None
    secret_values = collect_secret_values(config)

    def _scrub(value: object) -> object:
        return scrub_payload(value, secret_values=secret_values, project_root=project_root, app_path=app_path)

    return _scrub


__all__ = [
    "get_latest_trace_run_payload",
    "get_logs_payload",
    "get_metrics_payload",
    "get_trace_payload",
    "get_trace_run_payload",
    "get_trace_runs_payload",
    "get_traces_payload",
]
