from __future__ import annotations

from namel3ss.determinism import normalize_traces
from namel3ss.studio.agent_explain.summaries import (
    build_agent_run_summary,
    collect_ai_traces,
    extract_agent_step_context,
    extract_parallel_traces,
    extract_merge_summary,
    summarize_handoff_events,
)
from namel3ss.studio.agent_explain.timeline import build_agent_timeline


def build_agent_explain_payload(traces: list[dict], *, parallel: bool) -> dict:
    normalized = normalize_traces(traces)
    reasons, memory_facts = extract_agent_step_context(normalized)
    ai_traces = extract_parallel_traces(normalized) or collect_ai_traces(normalized)
    summaries = []
    for trace in ai_traces:
        agent_key = trace.get("agent_id") or trace.get("agent_name") or ""
        facts = memory_facts.get(agent_key) if agent_key else None
        if facts is None:
            facts = {"keys": [], "counts": {"total": 0}, "last_updated_step": None}
        summary = build_agent_run_summary(
            trace,
            memory_facts=facts,
            reason=reasons.get(agent_key) if agent_key else None,
        )
        summaries.append(summary)
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
    memory_facts_section = _memory_facts_section(summaries)
    payload = {
        "agent_run_summary": summaries[0] if len(summaries) == 1 and not parallel else None,
        "agent_parallel_summary": parallel_summary,
        "summaries": summaries,
        "timeline": timeline,
        "handoff": handoff_events,
        "memory_facts": memory_facts_section,
    }
    return payload


def _memory_facts_section(summaries: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for summary in summaries:
        facts = summary.get("memory_facts")
        if not isinstance(facts, dict):
            continue
        entry = {
            "agent_id": summary.get("agent_id") or "",
            "keys": list(facts.get("keys") or []),
            "counts": dict(facts.get("counts") or {}),
            "last_updated_step": facts.get("last_updated_step"),
        }
        agent_name = summary.get("agent_name")
        if isinstance(agent_name, str) and agent_name:
            entry["agent_name"] = agent_name
        role = summary.get("role")
        if isinstance(role, str) and role:
            entry["role"] = role
        entries.append(entry)
    return entries


__all__ = ["build_agent_explain_payload"]
