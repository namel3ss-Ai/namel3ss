from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_agent_merge_started(*, policy: str, candidate_count: int, title: str, lines: list[str]) -> dict:
    return {
        "type": TraceEventType.AGENT_MERGE_STARTED,
        "trace_version": TRACE_VERSION,
        "policy": policy,
        "candidate_count": int(candidate_count),
        "title": title,
        "lines": list(lines),
    }


def build_agent_merge_candidate(
    *,
    policy: str,
    agent_name: str,
    status: str,
    score: str | None,
    title: str,
    lines: list[str],
) -> dict:
    payload = {
        "type": TraceEventType.AGENT_MERGE_CANDIDATE,
        "trace_version": TRACE_VERSION,
        "policy": policy,
        "agent_name": agent_name,
        "status": status,
        "title": title,
        "lines": list(lines),
    }
    if score is not None:
        payload["score"] = score
    return payload


def build_agent_merge_selected(
    *,
    policy: str,
    agent_name: str,
    score: str | None,
    title: str,
    lines: list[str],
) -> dict:
    payload = {
        "type": TraceEventType.AGENT_MERGE_SELECTED,
        "trace_version": TRACE_VERSION,
        "policy": policy,
        "agent_name": agent_name,
        "title": title,
        "lines": list(lines),
    }
    if score is not None:
        payload["score"] = score
    return payload


def build_agent_merge_rejected(
    *,
    policy: str,
    agent_name: str,
    score: str | None,
    title: str,
    lines: list[str],
) -> dict:
    payload = {
        "type": TraceEventType.AGENT_MERGE_REJECTED,
        "trace_version": TRACE_VERSION,
        "policy": policy,
        "agent_name": agent_name,
        "title": title,
        "lines": list(lines),
    }
    if score is not None:
        payload["score"] = score
    return payload


def build_agent_merge_summary(
    *,
    policy: str,
    selected_agents: list[str],
    rejected_agents: list[str],
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.AGENT_MERGE_SUMMARY,
        "trace_version": TRACE_VERSION,
        "policy": policy,
        "selected_agents": list(selected_agents),
        "rejected_agents": list(rejected_agents),
        "title": title,
        "lines": list(lines),
    }


__all__ = [
    "build_agent_merge_candidate",
    "build_agent_merge_rejected",
    "build_agent_merge_selected",
    "build_agent_merge_started",
    "build_agent_merge_summary",
]
