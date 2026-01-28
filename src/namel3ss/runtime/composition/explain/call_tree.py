from __future__ import annotations

from namel3ss.traces.schema import TraceEventType

from namel3ss.runtime.composition.explain.bounds import MAX_CALLS, _apply_limit
from namel3ss.runtime.composition.explain.redaction import _list, _safe_text, _string


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
