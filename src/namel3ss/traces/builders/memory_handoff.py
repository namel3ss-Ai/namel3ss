from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_handoff_created(
    *,
    ai_profile: str,
    session: str,
    packet_id: str,
    from_agent_id: str,
    to_agent_id: str,
    team_id: str,
    phase_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_HANDOFF_CREATED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "packet_id": packet_id,
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "team_id": team_id,
        "phase_id": phase_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_handoff_applied(
    *,
    ai_profile: str,
    session: str,
    packet_id: str,
    from_agent_id: str,
    to_agent_id: str,
    item_count: int,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_HANDOFF_APPLIED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "packet_id": packet_id,
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "item_count": int(item_count),
        "title": title,
        "lines": list(lines),
    }


def build_memory_handoff_rejected(
    *,
    ai_profile: str,
    session: str,
    packet_id: str,
    from_agent_id: str,
    to_agent_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_HANDOFF_REJECTED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "packet_id": packet_id,
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_agent_briefing(
    *,
    ai_profile: str,
    session: str,
    packet_id: str,
    to_agent_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_AGENT_BRIEFING,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "packet_id": packet_id,
        "to_agent_id": to_agent_id,
        "title": title,
        "lines": list(lines),
    }


__all__ = [
    "build_memory_agent_briefing",
    "build_memory_handoff_applied",
    "build_memory_handoff_created",
    "build_memory_handoff_rejected",
]
