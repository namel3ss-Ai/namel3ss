from __future__ import annotations

from namel3ss.traces.schema import TraceEventType
from namel3ss.utils.json_tools import dumps_pretty


def print_explain_traces(output: dict) -> None:
    traces = output.get("traces") if isinstance(output, dict) else None
    if not isinstance(traces, list):
        print("Explain traces: none")
        return
    explain_types = {
        TraceEventType.BOUNDARY_START,
        TraceEventType.BOUNDARY_END,
        TraceEventType.EXPRESSION_EXPLAIN,
        TraceEventType.FLOW_START,
        TraceEventType.FLOW_STEP,
        TraceEventType.MUTATION_ALLOWED,
        TraceEventType.MUTATION_BLOCKED,
    }
    explain = [trace for trace in traces if trace.get("type") in explain_types]
    if not explain:
        print("Explain traces: none")
        return
    print("Explain traces:")
    print(dumps_pretty(explain))


__all__ = ["print_explain_traces"]
