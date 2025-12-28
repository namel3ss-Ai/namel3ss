from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_trust_check(
    *,
    ai_profile: str,
    session: str,
    action: str,
    actor_id: str,
    actor_level: str,
    required_level: str,
    allowed: bool,
    reason: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_TRUST_CHECK,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "action": action,
        "actor_id": actor_id,
        "actor_level": actor_level,
        "required_level": required_level,
        "allowed": bool(allowed),
        "reason": reason,
        "title": title,
        "lines": list(lines),
    }


def build_memory_approval_recorded(
    *,
    ai_profile: str,
    session: str,
    proposal_id: str,
    actor_id: str,
    count_now: int,
    count_required: int,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_APPROVAL_RECORDED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "proposal_id": proposal_id,
        "actor_id": actor_id,
        "count_now": int(count_now),
        "count_required": int(count_required),
        "title": title,
        "lines": list(lines),
    }


def build_memory_trust_rules(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_TRUST_RULES,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "title": title,
        "lines": list(lines),
    }
