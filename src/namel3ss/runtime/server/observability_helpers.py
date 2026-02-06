from __future__ import annotations


def load_observability_builder(kind: str):
    from namel3ss.runtime import observability_api

    mapping = {
        "logs": observability_api.get_logs_payload,
        "trace": observability_api.get_trace_payload,
        "traces": observability_api.get_traces_payload,
        "metrics": observability_api.get_metrics_payload,
    }
    return mapping.get(kind)


def observability_enabled() -> bool:
    from namel3ss.observability.enablement import observability_enabled as _enabled

    return _enabled()


def empty_observability_payload(kind: str) -> dict:
    if kind == "metrics":
        return {"ok": True, "counters": [], "timings": []}
    if kind in {"trace", "traces"}:
        return {"ok": True, "count": 0, "spans": []}
    return {"ok": True, "count": 0, "logs": []}


__all__ = ["empty_observability_payload", "load_observability_builder", "observability_enabled"]
