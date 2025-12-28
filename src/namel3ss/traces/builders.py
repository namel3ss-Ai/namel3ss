from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from namel3ss.traces.redact import redact_memory_item, redact_memory_items, summarize_payload, summarize_text
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def _base_event(event_type: str, *, call_id: str, provider: str, model: str) -> dict:
    return {
        "type": event_type,
        "trace_version": TRACE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "call_id": call_id,
    }


def build_ai_call_started(
    *,
    call_id: str,
    provider: str,
    model: str,
    input_text: str | None,
    tools_declared_count: int,
    memory_enabled: bool,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_STARTED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "input_summary": summarize_text(input_text),
            "tools_declared_count": tools_declared_count,
            "memory_enabled": bool(memory_enabled),
        }
    )
    return event


def build_ai_call_completed(
    *,
    call_id: str,
    provider: str,
    model: str,
    output_text: str | None,
    duration_ms: int,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_COMPLETED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "output_summary": summarize_text(output_text),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
        }
    )
    return event


def build_ai_call_failed(
    *,
    call_id: str,
    provider: str,
    model: str,
    error_type: str,
    error_message: str,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_FAILED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "error_type": error_type,
            "error_message": summarize_text(error_message),
            "duration_ms": duration_ms,
        }
    )
    return event


def build_tool_call_requested(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    arguments: Any,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_REQUESTED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments_summary": summarize_payload(arguments),
        }
    )
    return event


def build_tool_call_completed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    result: Any,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_COMPLETED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result_summary": summarize_payload(result),
            "duration_ms": duration_ms,
        }
    )
    return event


def build_tool_call_failed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    error_type: str,
    error_message: str,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_FAILED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "error_type": error_type,
            "error_message": summarize_text(error_message),
            "duration_ms": duration_ms,
        }
    )
    return event


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


def build_memory_explanation(
    *,
    for_event_index: int,
    title: str,
    lines: list[str],
    related_ids: list[str] | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_EXPLANATION,
        "trace_version": TRACE_VERSION,
        "for_event_index": int(for_event_index),
        "title": title,
        "lines": list(lines),
    }
    if related_ids:
        event["related_ids"] = list(related_ids)
    return event


def build_memory_links(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    phase_id: str,
    space: str,
    owner: str,
    link_count: int,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_LINKS,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "phase_id": phase_id,
        "space": space,
        "owner": owner,
        "link_count": int(link_count),
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_path(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    phase_id: str,
    space: str,
    owner: str,
    title: str,
    lines: list[str],
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_PATH,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "phase_id": phase_id,
        "space": space,
        "owner": owner,
        "title": title,
        "lines": list(lines),
    }
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_impact(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    space: str,
    owner: str,
    phase_id: str,
    depth_used: int,
    item_count: int,
    title: str,
    lines: list[str],
    path_lines: list[str] | None = None,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_IMPACT,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "space": space,
        "owner": owner,
        "phase_id": phase_id,
        "depth_used": int(depth_used),
        "item_count": int(item_count),
        "title": title,
        "lines": list(lines),
    }
    if path_lines is not None:
        event["path_lines"] = list(path_lines)
    if lane is not None:
        event["lane"] = lane
    return event


def build_memory_change_preview(
    *,
    ai_profile: str,
    session: str,
    memory_id: str,
    change_kind: str,
    title: str,
    lines: list[str],
    space: str | None = None,
    owner: str | None = None,
    phase_id: str | None = None,
    lane: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.MEMORY_CHANGE_PREVIEW,
        "trace_version": TRACE_VERSION,
        "ai_profile": ai_profile,
        "session": session,
        "memory_id": memory_id,
        "change_kind": change_kind,
        "title": title,
        "lines": list(lines),
    }
    if space is not None:
        event["space"] = space
    if owner is not None:
        event["owner"] = owner
    if phase_id is not None:
        event["phase_id"] = phase_id
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


__all__ = [
    "build_ai_call_completed",
    "build_ai_call_failed",
    "build_ai_call_started",
    "build_memory_recall",
    "build_memory_write",
    "build_memory_denied",
    "build_memory_forget",
    "build_memory_conflict",
    "build_memory_border_check",
    "build_memory_deleted",
    "build_memory_promoted",
    "build_memory_promotion_denied",
    "build_memory_phase_diff",
    "build_memory_phase_started",
    "build_memory_explanation",
    "build_memory_links",
    "build_memory_path",
    "build_memory_impact",
    "build_memory_change_preview",
    "build_memory_team_summary",
    "build_memory_proposed",
    "build_memory_approved",
    "build_memory_rejected",
    "build_memory_agreement_summary",
    "build_memory_trust_check",
    "build_memory_approval_recorded",
    "build_memory_trust_rules",
    "build_tool_call_completed",
    "build_tool_call_failed",
    "build_tool_call_requested",
]
