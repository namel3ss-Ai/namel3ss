from __future__ import annotations

from namel3ss.determinism import normalize_traces
from namel3ss.studio.agent_explain.summaries import (
    build_agent_run_summary,
    collect_ai_traces,
    extract_parallel_traces,
    extract_merge_summary,
    summarize_handoff_events,
)
from namel3ss.studio.agent_explain.timeline import build_agent_timeline


def build_agent_explain_payload(traces: list[dict], *, parallel: bool) -> dict:
    normalized = normalize_traces(traces)
    ai_traces = extract_parallel_traces(normalized) or collect_ai_traces(normalized)
    summaries = [build_agent_run_summary(trace) for trace in ai_traces]
    parallel_summary = None
    if parallel and summaries:
        merge_summary = extract_merge_summary(normalized)
        if merge_summary:
            parallel_summary = {
                "agents": summaries,
                "merge_policy": merge_summary.get("policy") or "preserve_order",
                "merge_explanation": list(merge_summary.get("lines") or []),
                "merge_selected": list(merge_summary.get("selected_agents") or []),
                "merge_rejected": list(merge_summary.get("rejected_agents") or []),
            }
        else:
            parallel_summary = {
                "agents": summaries,
                "merge_policy": "preserve_order",
                "merge_explanation": ["Parallel results are returned in declared order."],
            }
    handoff_events = summarize_handoff_events(normalized)
    timeline = build_agent_timeline(
        summaries,
        parallel_summary=parallel_summary,
        handoff_events=handoff_events,
    )
    payload = {
        "agent_run_summary": summaries[0] if len(summaries) == 1 and not parallel else None,
        "agent_parallel_summary": parallel_summary,
        "summaries": summaries,
        "timeline": timeline,
        "handoff": handoff_events,
    }
    return payload


__all__ = ["build_agent_explain_payload"]
