from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


def run_flow(program_ir, flow_name: str | None = None) -> dict:
    selected = _select_flow(program_ir, flow_name)
    result = execute_program_flow(program_ir, selected, state={}, input={}, store=MemoryStore())
    traces = [_trace_to_dict(t) for t in result.traces]
    return {"ok": True, "state": result.state, "result": result.last_value, "traces": traces}


def _select_flow(program_ir, flow_name: str | None) -> str:
    if flow_name:
        return flow_name
    if len(program_ir.flows) == 1:
        return program_ir.flows[0].name
    raise Namel3ssError('Multiple flows found; use: n3 <app.ai> flow "<name>"')


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    if isinstance(trace, dict):
        return trace
    return {"trace": trace}
