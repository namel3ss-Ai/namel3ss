from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_rule_applied(
    *,
    ai_profile: str,
    session: str,
    rule_id: str,
    rule_text: str,
    action: str,
    allowed: bool,
    reason: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_RULE_APPLIED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "rule_id": rule_id,
        "rule_text": rule_text,
        "action": action,
        "allowed": bool(allowed),
        "reason": reason,
        "title": title,
        "lines": list(lines),
    }


def build_memory_rules_snapshot(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_id: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_RULES_SNAPSHOT,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "phase_id": phase_id,
        "title": title,
        "lines": list(lines),
    }


def build_memory_rule_changed(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_from: str,
    phase_to: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.MEMORY_RULE_CHANGED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "team_id": team_id,
        "phase_from": phase_from,
        "phase_to": phase_to,
        "title": title,
        "lines": list(lines),
    }


__all__ = [
    "build_memory_rule_applied",
    "build_memory_rule_changed",
    "build_memory_rules_snapshot",
]
