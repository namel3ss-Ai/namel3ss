from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.execution.normalize import stable_truncate
from namel3ss.secrets import collect_secret_values
from namel3ss.traces.schema import TraceEventType

API_VERSION = "composition"

MAX_CALLS = 50
MAX_PIPELINE_RUNS = 25
MAX_PIPELINE_STEPS = 120
MAX_ORCHESTRATIONS = 25
MAX_BRANCHES = 50
MAX_MERGE_DETAILS = 50

_SAFE_PREFIXES = ("/api/", "/health", "/version", "/ui", "/docs/")
_INLINE_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\\\[^\\s]+")
_INLINE_POSIX_PATH = re.compile(r"/[^\\s]+")


def build_composition_explain_pack(
    run_payload: dict | None,
    *,
    project_root: str | Path | None = None,
    app_path: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict:
    if not isinstance(run_payload, dict):
        return _scrub(_empty_pack("no_run"), project_root, app_path, secret_values)
    traces = _coerce_traces(run_payload)
    flow_name = _flow_name(run_payload)
    pack = {
        "ok": bool(run_payload.get("ok", True)),
        "api_version": API_VERSION,
        "flow_name": flow_name,
        "call_tree": _build_call_tree(traces, flow_name),
        "pipelines": _build_pipeline_summary(traces),
        "orchestration": _build_orchestration_summary(traces),
    }
    return _scrub(pack, project_root, app_path, secret_values)


def build_composition_explain_bundle(
    root: Path,
    *,
    app_path: str | Path | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict:
    run_last = _load_last_run(root)
    return build_composition_explain_pack(
        run_last,
        project_root=root,
        app_path=app_path,
        secret_values=secret_values,
    )


def _empty_pack(reason: str) -> dict:
    return {
        "ok": False,
        "api_version": API_VERSION,
        "flow_name": "unknown",
        "reason": reason,
        "call_tree": {
            "root": {"id": "flow:unknown", "kind": "flow", "name": "unknown"},
            "calls": [],
            "total": 0,
            "truncated": False,
        },
        "pipelines": {
            "runs": [],
            "total_runs": 0,
            "total_steps": 0,
            "runs_truncated": False,
            "steps_truncated": False,
        },
        "orchestration": {
            "runs": [],
            "total_runs": 0,
            "runs_truncated": False,
        },
    }


def _coerce_traces(run_payload: dict) -> list[dict]:
    traces = run_payload.get("traces")
    if not isinstance(traces, list):
        contract = run_payload.get("contract") if isinstance(run_payload.get("contract"), dict) else {}
        traces = contract.get("traces") if isinstance(contract.get("traces"), list) else []
    return [trace for trace in traces if isinstance(trace, dict)]


def _flow_name(run_payload: dict) -> str:
    name = run_payload.get("flow_name")
    if isinstance(name, str) and name:
        return name
    contract = run_payload.get("contract") if isinstance(run_payload.get("contract"), dict) else {}
    name = contract.get("flow_name")
    if isinstance(name, str) and name:
        return name
    return "unknown"


def _build_call_tree(traces: list[dict], flow_name: str) -> dict:
    root_id = f"flow:{flow_name or 'unknown'}"
    flow_stack: list[str] = [root_id]
    calls: list[dict] = []
    call_index: dict[str, dict] = {}
    pipeline_index: dict[str, dict] = {}
    pipeline_stack: list[tuple[str, str]] = []
    pipeline_counter = 0
    anon_counter = 0

    for trace in traces:
        trace_type = trace.get("type")
        if trace_type == TraceEventType.FLOW_CALL_STARTED:
            anon_counter += 1
            call_id = _string(trace.get("flow_call_id")) or f"flow_call:{anon_counter:04d}"
            entry = {
                "id": call_id,
                "parent_id": flow_stack[-1] if flow_stack else root_id,
                "kind": "flow",
                "caller": _string(trace.get("caller_flow")),
                "callee": _string(trace.get("callee_flow")),
                "status": "running",
                "inputs": _list(trace.get("inputs")),
                "outputs": _list(trace.get("outputs")),
                "contract_inputs": _list(trace.get("contract_inputs")),
                "contract_outputs": _list(trace.get("contract_outputs")),
            }
            caller_purity = trace.get("caller_purity")
            if isinstance(caller_purity, str) and caller_purity:
                entry["caller_purity"] = caller_purity
            callee_purity = trace.get("callee_purity")
            if isinstance(callee_purity, str) and callee_purity:
                entry["callee_purity"] = callee_purity
            calls.append(entry)
            call_index[call_id] = entry
            flow_stack.append(call_id)
            continue
        if trace_type == TraceEventType.FLOW_CALL_FINISHED:
            call_id = _string(trace.get("flow_call_id"))
            entry = call_index.get(call_id or "")
            if entry is not None:
                status = trace.get("status")
                entry["status"] = status if isinstance(status, str) and status else "unknown"
                error_message = trace.get("error_message")
                if isinstance(error_message, str) and error_message:
                    entry["error_message"] = _safe_text(error_message)
            _pop_flow(flow_stack, call_id)
            continue
        if trace_type == TraceEventType.PIPELINE_STARTED:
            pipeline_counter += 1
            pipeline_name = _string(trace.get("pipeline")) or "unknown"
            run_id = f"pipeline:{pipeline_name}:{pipeline_counter:04d}"
            entry = {
                "id": run_id,
                "parent_id": flow_stack[-1] if flow_stack else root_id,
                "kind": "pipeline",
                "pipeline": pipeline_name,
                "status": "running",
            }
            calls.append(entry)
            pipeline_index[run_id] = entry
            pipeline_stack.append((pipeline_name, run_id))
            continue
        if trace_type == TraceEventType.PIPELINE_FINISHED:
            pipeline_name = _string(trace.get("pipeline")) or "unknown"
            run_id = _pop_pipeline(pipeline_stack, pipeline_name)
            if run_id and run_id in pipeline_index:
                entry = pipeline_index[run_id]
                status = trace.get("status")
                entry["status"] = status if isinstance(status, str) and status else "unknown"
                error_message = trace.get("error_message")
                if isinstance(error_message, str) and error_message:
                    entry["error_message"] = _safe_text(error_message)
            continue

    limited_calls, truncated = _apply_limit(calls, MAX_CALLS)
    return {
        "root": {"id": root_id, "kind": "flow", "name": flow_name or "unknown"},
        "calls": limited_calls,
        "total": len(calls),
        "truncated": truncated,
    }


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


def _build_orchestration_summary(traces: list[dict]) -> dict:
    runs: dict[str, dict] = {}
    order: list[str] = []
    branch_index: dict[str, dict] = {}

    for trace in traces:
        trace_type = trace.get("type")
        if trace_type == TraceEventType.ORCHESTRATION_BRANCH_STARTED:
            branch_id = _string(trace.get("branch_id")) or ""
            key = _orchestration_key_from_branch(branch_id)
            run = _get_orchestration_run(runs, order, key)
            branch = {
                "branch_id": branch_id,
                "branch_name": _string(trace.get("branch_name")) or "",
                "call_kind": _string(trace.get("call_kind")) or "",
                "call_target": _string(trace.get("call_target")) or "",
                "status": "running",
            }
            run["branches"].append(branch)
            branch_index[branch_id] = branch
            continue
        if trace_type == TraceEventType.ORCHESTRATION_BRANCH_FINISHED:
            branch_id = _string(trace.get("branch_id")) or ""
            branch = branch_index.get(branch_id)
            if branch is None:
                key = _orchestration_key_from_branch(branch_id)
                run = _get_orchestration_run(runs, order, key)
                branch = {
                    "branch_id": branch_id,
                    "branch_name": _string(trace.get("branch_name")) or "",
                    "call_kind": "",
                    "call_target": "",
                    "status": "unknown",
                }
                run["branches"].append(branch)
                branch_index[branch_id] = branch
            status = trace.get("status")
            branch["status"] = status if isinstance(status, str) and status else "unknown"
            error_message = trace.get("error_message")
            if isinstance(error_message, str) and error_message:
                branch["error_message"] = _safe_text(error_message)
            continue
        if trace_type == TraceEventType.ORCHESTRATION_MERGE_STARTED:
            merge_id = _string(trace.get("merge_id")) or ""
            key = _orchestration_key_from_merge(merge_id)
            run = _get_orchestration_run(runs, order, key)
            policy = _string(trace.get("policy")) or ""
            run["merge"] = {
                "merge_id": merge_id,
                "policy": policy,
                "status": "running",
            }
            continue
        if trace_type == TraceEventType.ORCHESTRATION_MERGE_FINISHED:
            merge_id = _string(trace.get("merge_id")) or ""
            key = _orchestration_key_from_merge(merge_id)
            run = _get_orchestration_run(runs, order, key)
            merge = run.get("merge") or {
                "merge_id": merge_id,
                "policy": _string(trace.get("policy")) or "",
                "status": "unknown",
            }
            status = trace.get("status")
            merge["status"] = status if isinstance(status, str) and status else "unknown"
            selected = trace.get("selected")
            if isinstance(selected, str) and selected:
                merge["selected"] = selected
            decision = trace.get("decision") if isinstance(trace.get("decision"), dict) else None
            if decision:
                merge.update(_summarize_merge_decision(decision))
            error_message = trace.get("error_message")
            if isinstance(error_message, str) and error_message:
                merge["error_message"] = _safe_text(error_message)
            run["merge"] = merge
            continue

    ordered_runs = [runs[key] for key in order]
    limited_runs, truncated = _apply_limit(ordered_runs, MAX_ORCHESTRATIONS)
    for run in limited_runs:
        branches = run.get("branches") or []
        limited_branches, branch_truncated = _apply_limit(list(branches), MAX_BRANCHES)
        run["branches"] = limited_branches
        run["branch_total"] = len(branches)
        run["branches_truncated"] = branch_truncated
    return {
        "runs": limited_runs,
        "total_runs": len(ordered_runs),
        "runs_truncated": truncated,
    }


def _summarize_merge_decision(decision: dict) -> dict:
    summary = {
        "policy": _string(decision.get("policy")) or "",
        "status": _string(decision.get("status")) or "",
    }
    selected = decision.get("selected")
    if isinstance(selected, str) and selected:
        summary["selected"] = selected
    reason = decision.get("reason")
    if isinstance(reason, str) and reason:
        summary["reason"] = _safe_text(reason)
    failed = decision.get("failed")
    if isinstance(failed, list):
        summary["failed"] = [str(item) for item in failed]
    precedence = decision.get("precedence")
    if isinstance(precedence, list):
        summary["precedence"] = [str(item) for item in precedence]
    branches = decision.get("branches")
    if isinstance(branches, list):
        items = [
            {
                "name": _string(item.get("name")) or "",
                "status": _string(item.get("status")) or "",
                "summary": _string(item.get("summary")) or "",
                "error_type": _string(item.get("error_type")) or "",
                "error_message": _safe_text(item.get("error_message")) if isinstance(item.get("error_message"), str) else None,
            }
            for item in branches
            if isinstance(item, dict)
        ]
        limited, truncated = _apply_limit(items, MAX_MERGE_DETAILS)
        summary["branches"] = limited
        summary["branches_total"] = len(items)
        summary["branches_truncated"] = truncated
    return summary


def _apply_limit(items: list[dict], limit: int) -> tuple[list[dict], bool]:
    if len(items) <= limit:
        return items, False
    return items[:limit], True


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


def _pop_flow(stack: list[str], call_id: str | None) -> None:
    if not call_id:
        return
    if stack and stack[-1] == call_id:
        stack.pop()
        return
    for idx in range(len(stack) - 1, -1, -1):
        if stack[idx] == call_id:
            stack.pop(idx)
            return


def _pop_pipeline(stack: list[tuple[str, str]], pipeline_name: str) -> str | None:
    for idx in range(len(stack) - 1, -1, -1):
        name, run_id = stack[idx]
        if name == pipeline_name:
            stack.pop(idx)
            return run_id
    return None


def _orchestration_key_from_branch(branch_id: str) -> str:
    parts = branch_id.split(":") if branch_id else []
    if len(parts) >= 3 and parts[0] == "branch":
        return f"{parts[1]}:{parts[2]}"
    return "unknown"


def _orchestration_key_from_merge(merge_id: str) -> str:
    parts = merge_id.split(":") if merge_id else []
    if len(parts) >= 3 and parts[0] == "merge":
        return f"{parts[1]}:{parts[2]}"
    return "unknown"


def _get_orchestration_run(runs: dict[str, dict], order: list[str], key: str) -> dict:
    if key not in runs:
        runs[key] = {
            "orchestration_id": key,
            "branches": [],
            "merge": None,
        }
        order.append(key)
    return runs[key]


def _safe_text(value: object) -> str:
    text = _string(value)
    if not text:
        return ""
    cleaned = _scrub_inline_paths(text)
    return stable_truncate(cleaned, limit=200)


def _scrub_inline_paths(text: str) -> str:
    def _replace_posix(match: re.Match) -> str:
        path = match.group(0)
        if path.startswith(_SAFE_PREFIXES):
            return path
        return "<path>"

    cleaned = _INLINE_WINDOWS_PATH.sub("<path>", text)
    cleaned = _INLINE_POSIX_PATH.sub(_replace_posix, cleaned)
    return cleaned


def _string(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _scrub(
    payload: dict,
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: Iterable[str] | None,
) -> dict:
    secrets = list(secret_values) if secret_values is not None else collect_secret_values()
    scrubbed = scrub_payload(payload, secret_values=secrets, project_root=project_root, app_path=app_path)
    return scrubbed if isinstance(scrubbed, dict) else payload


def _load_last_run(root: Path) -> dict | None:
    path = root / ".namel3ss" / "run" / "last.json"
    return _load_json(path)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = [
    "API_VERSION",
    "MAX_CALLS",
    "MAX_PIPELINE_RUNS",
    "MAX_PIPELINE_STEPS",
    "MAX_ORCHESTRATIONS",
    "MAX_BRANCHES",
    "MAX_MERGE_DETAILS",
    "build_composition_explain_pack",
    "build_composition_explain_bundle",
]
