from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.observability.enablement import observability_enabled
from namel3ss.observability.log_store import read_logs
from namel3ss.observability.metrics_store import read_metrics
from namel3ss.observability.scrub import scrub_payload
from namel3ss.observability.trace_store import read_spans
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


__all__ = ["get_logs_payload", "get_metrics_payload", "get_trace_payload", "get_traces_payload"]
