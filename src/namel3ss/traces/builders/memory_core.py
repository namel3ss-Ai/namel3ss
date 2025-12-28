from __future__ import annotations

from namel3ss.traces.redact import redact_memory_item, redact_memory_items, summarize_text
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_memory_recall(
    *,
    ai_profile: str,
    session: str,
    query: str,
    recalled: list[dict],
    policy: dict,
    deterministic_hash: str,
    spaces_consulted: list[str] | None = None,
    recall_counts: dict | None = None,
    phase_counts: dict | None = None,
    current_phase: dict | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_RECALL,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "query": summarize_text(query),
        "recalled": redact_memory_items(recalled),
        "policy": policy,
        "deterministic_hash": deterministic_hash,
    }
    if spaces_consulted is not None:
        event["spaces_consulted"] = list(spaces_consulted)
    if recall_counts is not None:
        event["recall_counts"] = dict(recall_counts)
    if phase_counts is not None:
        event["phase_counts"] = dict(phase_counts)
    if current_phase is not None:
        event["current_phase"] = dict(current_phase)
    return event


def build_memory_write(
    *,
    ai_profile: str,
    session: str,
    written: list[dict],
    reason: str,
) -> dict:
    return {
        "type": TraceEventType.MEMORY_WRITE,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "written": redact_memory_items(written),
        "reason": reason,
    }


def build_memory_denied(
    *,
    ai_profile: str,
    session: str,
    attempted: dict,
    reason: str,
    policy_snapshot: dict,
    explanation: dict | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_DENIED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "attempted": redact_memory_item(attempted),
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if explanation is not None:
        event["explanation"] = explanation
    return event


def build_memory_forget(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    reason: str,
    policy_snapshot: dict,
    explanation: dict | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_FORGET,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if explanation is not None:
        event["explanation"] = explanation
    return event


def build_memory_conflict(
    *,
    ai_profile: str,
    session: str,
    winner_id: str,
    loser_id: str,
    rule: str,
    dedup_key: str,
    explanation: dict | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_CONFLICT,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "winner_id": winner_id,
        "loser_id": loser_id,
        "rule": rule,
        "dedup_key": dedup_key,
    }
    if explanation is not None:
        event["explanation"] = explanation
    return event


def build_memory_border_check(
    *,
    ai_profile: str,
    session: str,
    action: str,
    from_space: str,
    to_space: str | None,
    allowed: bool,
    reason: str,
    policy_snapshot: dict,
    subject_id: str | None = None,
    from_lane: str | None = None,
    to_lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_BORDER_CHECK,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "action": action,
        "from_space": from_space,
        "allowed": bool(allowed),
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if to_space is not None:
        event["to_space"] = to_space
    if from_lane is not None:
        event["from_lane"] = from_lane
    if to_lane is not None:
        event["to_lane"] = to_lane
    if subject_id is not None:
        event["subject_id"] = subject_id
    return event


def build_memory_promoted(
    *,
    ai_profile: str,
    session: str,
    from_space: str,
    to_space: str,
    from_id: str,
    to_id: str,
    authority_used: str,
    reason: str,
    policy_snapshot: dict,
    from_lane: str | None = None,
    to_lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PROMOTED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "from_space": from_space,
        "to_space": to_space,
        "from_id": from_id,
        "to_id": to_id,
        "authority_used": authority_used,
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if from_lane is not None:
        event["from_lane"] = from_lane
    if to_lane is not None:
        event["to_lane"] = to_lane
    return event


def build_memory_promotion_denied(
    *,
    ai_profile: str,
    session: str,
    from_space: str,
    to_space: str,
    memory_id: str,
    allowed: bool,
    reason: str,
    policy_snapshot: dict,
    from_lane: str | None = None,
    to_lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PROMOTION_DENIED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "from_space": from_space,
        "to_space": to_space,
        "memory_id": memory_id,
        "allowed": bool(allowed),
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if from_lane is not None:
        event["from_lane"] = from_lane
    if to_lane is not None:
        event["to_lane"] = to_lane
    return event


def build_memory_phase_started(
    *,
    ai_profile: str,
    session: str,
    space: str,
    owner: str,
    phase_id: str,
    phase_name: str | None,
    reason: str,
    policy_snapshot: dict,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PHASE_STARTED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "owner": owner,
        "phase_id": phase_id,
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if phase_name:
        event["phase_name"] = phase_name
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_deleted(
    *,
    ai_profile: str,
    session: str,
    space: str,
    owner: str,
    phase_id: str,
    memory_id: str,
    reason: str,
    policy_snapshot: dict,
    replaced_by: str | None = None,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_DELETED,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "owner": owner,
        "phase_id": phase_id,
        "memory_id": memory_id,
        "reason": reason,
        "policy_snapshot": policy_snapshot,
    }
    if replaced_by:
        event["replaced_by"] = replaced_by
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_phase_diff(
    *,
    ai_profile: str,
    session: str,
    space: str,
    owner: str,
    from_phase_id: str,
    to_phase_id: str,
    added_count: int,
    deleted_count: int,
    replaced_count: int,
    top_changes: list[dict],
    summary_lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PHASE_DIFF,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "space": space,
        "owner": owner,
        "from_phase_id": from_phase_id,
        "to_phase_id": to_phase_id,
        "added_count": added_count,
        "deleted_count": deleted_count,
        "replaced_count": replaced_count,
        "top_changes": list(top_changes),
        "summary_lines": list(summary_lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_team_summary(
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
        "type": TraceEventType.MEMORY_TEAM_SUMMARY,
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
