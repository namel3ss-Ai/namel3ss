from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_proposed(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_id: str,
    proposal_id: str,
    memory_id: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PROPOSED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "phase_id": phase_id,
        "proposal_id": proposal_id,
        "memory_id": memory_id,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_approved(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_id: str,
    proposal_id: str,
    memory_id: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_APPROVED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "phase_id": phase_id,
        "proposal_id": proposal_id,
        "memory_id": memory_id,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_rejected(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_id: str,
    proposal_id: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_REJECTED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "phase_id": phase_id,
        "proposal_id": proposal_id,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_agreement_summary(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    space: str,
    phase_from: str,
    phase_to: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_AGREEMENT_SUMMARY,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "space": space,
        "phase_from": phase_from,
        "phase_to": phase_to,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event
