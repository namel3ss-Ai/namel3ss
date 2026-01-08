from __future__ import annotations

from typing import Any

from namel3ss.traces.redact import summarize_text


def build_agent_timeline(
    summaries: list[dict],
    *,
    parallel_summary: dict | None = None,
    handoff_events: list[dict] | None = None,
) -> list[dict]:
    events: list[dict] = []
    for summary in summaries:
        agent_id = summary.get("agent_id") or summary.get("ai_profile") or "agent"
        events.append(
            {
                "id": f"{agent_id}:start",
                "kind": "start",
                "title": f"{agent_id} started",
                "details": {"input_summary": summary.get("input_summary") or ""},
            }
        )
        memory = summary.get("memory") if isinstance(summary.get("memory"), dict) else {}
        recalled = memory.get("recalled_count", 0)
        if recalled or memory.get("reasons"):
            events.append(
                {
                    "id": f"{agent_id}:memory",
                    "kind": "memory",
                    "title": f"{agent_id} recalled memory",
                    "details": {
                        "recalled_count": recalled,
                        "spaces": list(memory.get("spaces") or []),
                    },
                    "explain": _memory_explain(memory),
                }
            )
        tools = summary.get("tools") if isinstance(summary.get("tools"), list) else []
        for idx, tool in enumerate(tools, start=1):
            tool_name = tool.get("tool") or "tool"
            status = tool.get("status") or "requested"
            title = f"{agent_id} tool {tool_name}"
            events.append(
                {
                    "id": f"{agent_id}:tool:{idx}",
                    "kind": "tool",
                    "title": title,
                    "details": {
                        "status": status,
                        "decision": tool.get("decision"),
                    },
                    "explain": _tool_explain(tool),
                }
            )
        events.append(
            {
                "id": f"{agent_id}:output",
                "kind": "output",
                "title": f"{agent_id} output",
                "details": {
                    "output_preview": summary.get("output_preview") or "",
                    "output_hash": summary.get("output_hash") or "",
                },
            }
        )
    if parallel_summary:
        events.append(
            {
                "id": "parallel:merge",
                "kind": "merge",
                "title": "Parallel results merged",
                "details": {
                    "merge_policy": parallel_summary.get("merge_policy") or "preserve_order",
                },
                "explain": {
                    "title": "Merge decision",
                    "lines": list(parallel_summary.get("merge_explanation") or []),
                },
            }
        )
    for handoff in handoff_events or []:
        if not isinstance(handoff, dict):
            continue
        title = handoff.get("title") or "Handoff"
        event_id = f"handoff:{handoff.get('packet_id') or ''}:{handoff.get('type')}"
        events.append(
            {
                "id": event_id,
                "kind": "handoff",
                "title": title,
                "details": {
                    "from_agent_id": handoff.get("from_agent_id"),
                    "to_agent_id": handoff.get("to_agent_id"),
                },
                "explain": {
                    "title": title,
                    "lines": list(handoff.get("lines") or []),
                },
            }
        )
    return events


def _memory_explain(memory: dict) -> dict:
    reasons = memory.get("reasons") if isinstance(memory.get("reasons"), list) else []
    lines = [summarize_text(reason) for reason in reasons if reason]
    if not lines:
        lines = ["No policy explanations recorded."]
    return {
        "title": "Memory policy",
        "lines": lines,
    }


def _tool_explain(tool: dict) -> dict:
    lines: list[str] = []
    args = tool.get("arguments_summary")
    if isinstance(args, str) and args:
        lines.append(f"args: {summarize_text(args)}")
    result = tool.get("result_summary")
    if isinstance(result, str) and result:
        lines.append(f"result: {summarize_text(result)}")
    reason = tool.get("decision_reason")
    if isinstance(reason, str) and reason:
        lines.append(f"reason: {summarize_text(reason)}")
    if not lines:
        lines = ["No tool details recorded."]
    return {"title": "Tool decision", "lines": lines}


__all__ = ["build_agent_timeline"]
