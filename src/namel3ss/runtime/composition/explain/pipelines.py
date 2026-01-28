from __future__ import annotations

from namel3ss.traces.schema import TraceEventType

from namel3ss.runtime.composition.explain.bounds import (
    MAX_PIPELINE_RUNS,
    MAX_PIPELINE_STEPS,
    _apply_limit,
)
from namel3ss.runtime.composition.explain.redaction import _safe_text, _string


def _build_pipeline_summary(traces: list[dict]) -> dict:
    runs: list[dict] = []
    active: list[dict] = []
    counter = 0

    for trace in traces:
        trace_type = trace.get("type")
        if trace_type == TraceEventType.PIPELINE_STARTED:
            counter += 1
            pipeline_name = _string(trace.get("pipeline")) or "unknown"
            run = {
                "run_id": f"pipeline:{pipeline_name}:{counter:04d}",
                "pipeline": pipeline_name,
                "status": "running",
                "steps": [],
            }
            runs.append(run)
            active.append(run)
            continue
        if trace_type == TraceEventType.PIPELINE_STEP:
            pipeline_name = _string(trace.get("pipeline")) or "unknown"
            run = _find_active(active, pipeline_name)
            if run is None:
                counter += 1
                run = {
                    "run_id": f"pipeline:{pipeline_name}:{counter:04d}",
                    "pipeline": pipeline_name,
                    "status": "unknown",
                    "steps": [],
                    "implicit": True,
                }
                runs.append(run)
                active.append(run)
            step = {
                "step_id": _string(trace.get("step_id")) or "",
                "step_kind": _string(trace.get("step_kind")) or "",
                "status": _string(trace.get("status")) or "unknown",
                "summary": trace.get("summary") if isinstance(trace.get("summary"), dict) else {},
                "checksum": _string(trace.get("checksum")) or "",
                "ordinal": int(trace.get("ordinal") or 0),
            }
            run["steps"].append(step)
            continue
        if trace_type == TraceEventType.PIPELINE_FINISHED:
            pipeline_name = _string(trace.get("pipeline")) or "unknown"
            run = _find_active(active, pipeline_name)
            if run is not None:
                status = trace.get("status")
                run["status"] = status if isinstance(status, str) and status else "unknown"
                error_message = trace.get("error_message")
                if isinstance(error_message, str) and error_message:
                    run["error_message"] = _safe_text(error_message)
                _remove_active(active, run)
            continue

    total_runs = len(runs)
    total_steps = sum(len(run.get("steps") or []) for run in runs)
    limited_runs, runs_truncated = _apply_limit(runs, MAX_PIPELINE_RUNS)
    steps_truncated = False
    for run in limited_runs:
        steps = run.get("steps") or []
        limited_steps, truncated = _apply_limit(list(steps), MAX_PIPELINE_STEPS)
        run["steps"] = limited_steps
        run["step_total"] = len(steps)
        if truncated:
            run["steps_truncated"] = True
            steps_truncated = True
        else:
            run["steps_truncated"] = False
    return {
        "runs": limited_runs,
        "total_runs": total_runs,
        "total_steps": total_steps,
        "runs_truncated": runs_truncated,
        "steps_truncated": steps_truncated,
    }


def _find_active(active: list[dict], pipeline_name: str) -> dict | None:
    for run in reversed(active):
        if run.get("pipeline") == pipeline_name:
            return run
    return None


def _remove_active(active: list[dict], run: dict) -> None:
    for idx in range(len(active) - 1, -1, -1):
        if active[idx] is run:
            active.pop(idx)
            return
