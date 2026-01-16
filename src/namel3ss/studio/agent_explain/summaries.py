from __future__ import annotations

import hashlib
import json
from typing import Any

from namel3ss.traces.redact import summarize_text


def build_agent_run_summary(
    trace: dict,
    *,
    memory_facts: dict | None = None,
    reason: str | None = None,
) -> dict:
    canonical_events = _list_events(trace.get("canonical_events"))
    input_summary = _input_summary(trace, canonical_events)
    output_value = trace.get("output")
    output_preview = summarize_text(output_value)
    output_hash = _hash_value(output_value)
    memory_summary = _memory_summary(canonical_events)
    tools_summary = _tool_summary(canonical_events)
    failures = _failure_codes(canonical_events)
    agent_id = trace.get("agent_id") or trace.get("agent_name") or ""
    agent_name = trace.get("agent_name") or ""
    summary = {
        "agent_id": agent_id,
        "ai_profile": trace.get("ai_profile_name") or trace.get("ai_name") or "",
        "input_summary": input_summary,
        "memory": memory_summary,
        "tools": tools_summary,
        "output_preview": output_preview,
        "output_hash": output_hash,
        "failures": failures,
    }
    if agent_name:
        summary["agent_name"] = agent_name
    role = trace.get("role")
    if isinstance(role, str) and role:
        summary["role"] = role
    if memory_facts is not None:
        summary["memory_facts"] = dict(memory_facts)
    if reason:
        summary["reason"] = reason
    return summary


def collect_ai_traces(traces: list[dict]) -> list[dict]:
    return [trace for trace in traces if isinstance(trace, dict) and trace.get("type") == "ai_call"]


def extract_parallel_traces(traces: list[dict]) -> list[dict] | None:
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        if trace.get("type") != "parallel_agents":
            continue
        agents = trace.get("agents")
        if isinstance(agents, list):
            return [entry for entry in agents if isinstance(entry, dict)]
    return None


def extract_merge_summary(traces: list[dict]) -> dict | None:
    summary_event = None
    explanation_lines: list[str] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        event_type = trace.get("type")
        if event_type == "agent_merge_summary":
            summary_event = trace
        elif event_type in {"agent_merge_selected", "agent_merge_rejected"}:
            agent_name = trace.get("agent_name") or "agent"
            lines = list(trace.get("lines") or [])
            explanation_lines.extend([f"{agent_name}: {line}" for line in lines])
    if summary_event is None:
        return None
    return {
        "policy": summary_event.get("policy") or "",
        "lines": list(summary_event.get("lines") or []) + explanation_lines,
        "selected_agents": list(summary_event.get("selected_agents") or []),
        "rejected_agents": list(summary_event.get("rejected_agents") or []),
    }


def summarize_handoff_events(traces: list[dict]) -> list[dict]:
    summaries: list[dict] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        event_type = trace.get("type")
        if event_type not in {"memory_handoff_created", "memory_handoff_applied", "memory_handoff_rejected"}:
            continue
        summaries.append(
            {
                "type": event_type,
                "packet_id": trace.get("packet_id"),
                "from_agent_id": trace.get("from_agent_id"),
                "to_agent_id": trace.get("to_agent_id"),
                "title": trace.get("title") or "",
                "lines": list(trace.get("lines") or []),
            }
        )
    return summaries


def extract_agent_step_context(traces: list[dict]) -> tuple[dict[str, str], dict[str, dict]]:
    reasons: dict[str, str] = {}
    memory_facts: dict[str, dict] = {}
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        key = _agent_key(trace)
        if not key:
            continue
        event_type = trace.get("type")
        if event_type == "agent_step_start":
            reason = _first_line(trace)
            if reason:
                reasons.setdefault(key, reason)
        elif event_type == "agent_step_end":
            facts = trace.get("memory_facts")
            if isinstance(facts, dict):
                memory_facts[key] = dict(facts)
    return reasons, memory_facts


def _list_events(value: Any) -> list[dict]:
    if isinstance(value, list):
        return [event for event in value if isinstance(event, dict)]
    return []


def _input_summary(trace: dict, canonical_events: list[dict]) -> str:
    for event in canonical_events:
        if event.get("type") == "ai_call_started" and isinstance(event.get("input_summary"), str):
            return event["input_summary"]
    return summarize_text(trace.get("input"))


def _memory_summary(canonical_events: list[dict]) -> dict:
    recall_event = None
    for event in canonical_events:
        if event.get("type") == "memory_recall":
            recall_event = event
            break
    recalled_count = 0
    spaces = []
    recall_counts = {}
    if isinstance(recall_event, dict):
        recalled = recall_event.get("recalled")
        if isinstance(recalled, list):
            recalled_count = len(recalled)
        recall_counts = recall_event.get("recall_counts") if isinstance(recall_event.get("recall_counts"), dict) else {}
        spaces = list(recall_event.get("spaces_consulted") or [])
    if recall_counts:
        recalled_count = sum(int(value) for value in recall_counts.values())
        if not spaces:
            spaces = list(recall_counts.keys())
    reasons = _memory_reasons(canonical_events)
    space_counts = [
        {"space": key, "count": int(recall_counts[key])}
        for key in sorted(recall_counts.keys())
    ]
    return {
        "recalled_count": recalled_count,
        "spaces": list(spaces),
        "space_counts": space_counts,
        "reasons": reasons,
    }


def _memory_reasons(canonical_events: list[dict]) -> list[str]:
    reasons: list[str] = []
    for event in canonical_events:
        if event.get("type") != "memory_border_check":
            continue
        reason = event.get("reason")
        if not isinstance(reason, str) or not reason:
            continue
        if reason in reasons:
            continue
        reasons.append(reason)
    return reasons[:3]


def _tool_summary(canonical_events: list[dict]) -> list[dict]:
    tool_map: dict[str, dict] = {}
    order: list[str] = []
    declared_count = None
    for event in canonical_events:
        if event.get("type") == "ai_call_started":
            declared_count = event.get("tools_declared_count")
        event_type = event.get("type")
        if event_type == "tool_call_requested":
            tool_call_id = str(event.get("tool_call_id") or "")
            if not tool_call_id:
                continue
            entry = tool_map.get(tool_call_id)
            if not entry:
                entry = {"tool": event.get("tool_name") or "", "status": "requested"}
                tool_map[tool_call_id] = entry
                order.append(tool_call_id)
            args_summary = event.get("arguments_summary")
            if isinstance(args_summary, str):
                entry["arguments_summary"] = args_summary
        elif event_type == "tool_call_completed":
            tool_call_id = str(event.get("tool_call_id") or "")
            entry = tool_map.get(tool_call_id)
            if not entry:
                entry = {"tool": event.get("tool_name") or "", "status": "completed"}
                tool_map[tool_call_id] = entry
                order.append(tool_call_id)
            entry["status"] = "completed"
            result_summary = event.get("result_summary")
            if isinstance(result_summary, str):
                entry["result_summary"] = result_summary
            entry["decision"] = "allowed"
            entry["decision_reason"] = "tool call completed"
        elif event_type == "tool_call_failed":
            tool_call_id = str(event.get("tool_call_id") or "")
            entry = tool_map.get(tool_call_id)
            if not entry:
                entry = {"tool": event.get("tool_name") or "", "status": "failed"}
                tool_map[tool_call_id] = entry
                order.append(tool_call_id)
            entry["status"] = "failed"
            entry["decision"] = "blocked"
            error_message = event.get("error_message")
            if isinstance(error_message, str):
                entry["decision_reason"] = error_message
            error_type = event.get("error_type")
            if isinstance(error_type, str):
                entry["error_type"] = error_type
    tools = [tool_map[tool_call_id] for tool_call_id in order if tool_call_id in tool_map]
    if declared_count and not tools:
        tools.append({"tool": "", "status": "none", "decision": "unused", "decision_reason": "no tool calls recorded"})
    return tools


def _failure_codes(canonical_events: list[dict]) -> list[str]:
    codes: list[str] = []
    for event in canonical_events:
        event_type = event.get("type")
        if event_type == "ai_call_failed":
            error_type = event.get("error_type")
            if isinstance(error_type, str):
                codes.append(f"ai_call_failed:{error_type}")
            else:
                codes.append("ai_call_failed")
        if event_type == "tool_call_failed":
            tool_name = event.get("tool_name")
            if isinstance(tool_name, str) and tool_name:
                codes.append(f"tool_call_failed:{tool_name}")
            else:
                codes.append("tool_call_failed")
    seen = set()
    ordered: list[str] = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        ordered.append(code)
    return ordered


def _agent_key(trace: dict) -> str:
    for key in ("agent_id", "agent_name"):
        value = trace.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _first_line(trace: dict) -> str | None:
    lines = trace.get("lines")
    if isinstance(lines, list) and lines:
        line = lines[0]
        if isinstance(line, str):
            return line
    return None


def _hash_value(value: object) -> str:
    canonical = _canonicalize_value(value)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonicalize_value(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, set):
        return [_canonicalize_value(item) for item in sorted(value, key=str)]
    return value


__all__ = [
    "build_agent_run_summary",
    "collect_ai_traces",
    "extract_agent_step_context",
    "extract_parallel_traces",
    "summarize_handoff_events",
]
