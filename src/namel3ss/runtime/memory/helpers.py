from __future__ import annotations

from dataclasses import replace
from typing import Optional

from namel3ss.runtime.memory.contract import MemoryItem, normalize_memory_item
from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_FACT,
    EVENT_PREFERENCE,
    build_dedupe_key,
    is_low_signal,
)
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta
from namel3ss.runtime.memory_policy.explain import explain_conflict, explain_forget, explain_write_decision
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta
from namel3ss.runtime.memory_policy.model import (
    AUTHORITY_AI,
    AUTHORITY_SYSTEM,
    AUTHORITY_TOOL,
    AUTHORITY_USER,
)
from namel3ss.traces.builders import (
    build_memory_border_check,
    build_memory_conflict,
    build_memory_deleted,
    build_memory_denied,
    build_memory_forget,
)


def should_attempt_semantic(event_type: str, text: str, write_policy: str) -> bool:
    if not text or not text.strip():
        return False
    if is_low_signal(text):
        return False
    if event_type == EVENT_CONTEXT:
        return write_policy == "aggressive"
    if write_policy == "minimal":
        return event_type in {EVENT_FACT, EVENT_PREFERENCE, EVENT_DECISION, EVENT_CORRECTION}
    return True


def should_attempt_profile(event_type: str) -> bool:
    return event_type in {EVENT_FACT, EVENT_CORRECTION}


def authority_for_source(source: str) -> tuple[str, str]:
    if source == "user":
        return AUTHORITY_USER, "source:user"
    if source == "ai":
        return AUTHORITY_AI, "source:ai"
    if source == "tool":
        return AUTHORITY_TOOL, "source:tool"
    return AUTHORITY_SYSTEM, f"source:{source}"


def build_meta(
    event_type: str,
    importance_reason: list[str],
    text: str,
    *,
    authority: str,
    authority_reason: str,
    space: str,
    owner: str,
    lane: str,
    phase=None,
    dedup_key: Optional[str] = None,
    promotion_target: str | None = None,
    promotion_reason: str | None = None,
    visible_to: str | None = None,
    can_change: bool | None = None,
    allow_team_change: bool = True,
    agent_id: str | None = None,
) -> dict:
    meta = {
        "event_type": event_type,
        "importance_reason": importance_reason,
        "dedup_key": dedup_key or build_dedupe_key(event_type, text),
        "authority": authority,
        "authority_reason": authority_reason,
        "space": space,
        "owner": owner,
    }
    meta = ensure_lane_meta(
        meta,
        lane=lane,
        visible_to=visible_to,
        can_change=can_change,
        allow_team_change=allow_team_change,
        agent_id=agent_id,
    )
    if phase is not None:
        meta = apply_phase_meta(meta, phase)
    if promotion_target:
        meta["promotion_target"] = promotion_target
    if promotion_reason:
        meta["promotion_reason"] = promotion_reason
    return meta


def with_policy_tags(item: MemoryItem, tags: list[str]) -> MemoryItem:
    if not tags:
        return item
    meta = dict(item.meta)
    existing = list(meta.get("policy_tags", []))
    for tag in tags:
        if tag not in existing:
            existing.append(tag)
    meta["policy_tags"] = existing
    return replace(item, meta=meta)


def build_denied_event(ai_profile: str, session: str, item: MemoryItem, decision, policy_snapshot: dict) -> dict:
    event_type = item.meta.get("event_type", EVENT_CONTEXT)
    explanation = explain_write_decision(decision, kind=item.kind.value, event_type=event_type)
    return build_memory_denied(
        ai_profile=ai_profile,
        session=session,
        attempted=normalize_memory_item(item),
        reason=decision.reason,
        policy_snapshot=policy_snapshot,
        explanation=explanation,
    )


def build_conflict_event(ai_profile: str, session: str, decision) -> dict:
    dedup_key = decision.winner.meta.get("dedup_key") or decision.loser.meta.get("dedup_key")
    if not dedup_key:
        key = decision.winner.meta.get("key") or decision.loser.meta.get("key")
        if key:
            dedup_key = f"fact:{key}"
    return build_memory_conflict(
        ai_profile=ai_profile,
        session=session,
        winner_id=decision.winner.id,
        loser_id=decision.loser.id,
        rule=decision.rule,
        dedup_key=dedup_key or "unknown",
        explanation=explain_conflict(decision),
    )


def build_forget_event(
    ai_profile: str,
    session: str,
    item: MemoryItem,
    reason: str,
    policy_snapshot: dict,
) -> dict:
    return build_memory_forget(
        ai_profile=ai_profile,
        session=session,
        memory_id=item.id,
        reason=reason,
        policy_snapshot=policy_snapshot,
        explanation=explain_forget(item, reason=reason),
    )


def build_forget_events(ai_profile: str, session: str, forgotten, policy_snapshot) -> list[dict]:
    snapshot = policy_snapshot.as_dict() if hasattr(policy_snapshot, "as_dict") else policy_snapshot
    events: list[dict] = []
    for item, reason in forgotten:
        events.append(build_forget_event(ai_profile, session, item, reason, snapshot))
    return events


def build_deleted_event(
    ai_profile: str,
    session: str,
    *,
    space: str,
    owner: str,
    phase,
    item: MemoryItem,
    reason: str,
    policy_snapshot: dict,
    replaced_by: str | None,
) -> dict:
    phase_id = getattr(phase, "phase_id", None) if phase is not None else None
    phase_id = phase_id or item.meta.get("phase_id") or "phase-unknown"
    lane = item.meta.get("lane") if hasattr(item, "meta") else None
    return build_memory_deleted(
        ai_profile=ai_profile,
        session=session,
        space=space,
        owner=owner,
        phase_id=phase_id,
        memory_id=item.id,
        reason=reason,
        policy_snapshot=policy_snapshot,
        replaced_by=replaced_by,
        lane=lane,
    )


def build_deleted_events(
    ai_profile: str,
    session: str,
    *,
    space: str,
    owner: str,
    phase,
    removed: list[MemoryItem],
    reason: str,
    policy_snapshot: dict,
    replaced_by: str | None,
) -> list[dict]:
    return [
        build_deleted_event(
            ai_profile,
            session,
            space=space,
            owner=owner,
            phase=phase,
            item=item,
            reason=reason,
            policy_snapshot=policy_snapshot,
            replaced_by=replaced_by,
        )
        for item in removed
    ]


def build_border_event(
    *,
    ai_profile: str,
    session: str,
    action: str,
    from_space: str,
    to_space: str | None,
    allowed: bool,
    reason: str,
    subject_id: str | None,
    policy_snapshot: dict,
    from_lane: str | None = None,
    to_lane: str | None = None,
) -> dict:
    return build_memory_border_check(
        ai_profile=ai_profile,
        session=session,
        action=action,
        from_space=from_space,
        to_space=to_space,
        allowed=allowed,
        reason=reason,
        subject_id=subject_id,
        policy_snapshot=policy_snapshot,
        from_lane=from_lane,
        to_lane=to_lane,
    )


def apply_recall_policy_tags(context: dict, contract) -> None:
    retention = contract.retention
    for kind, items in context.items():
        for item in items:
            meta = item.get("meta") or {}
            tags = list(meta.get("policy_tags", []))
            event_type = meta.get("event_type", EVENT_CONTEXT)
            rule = retention.get(kind, {}).get(event_type) or retention.get(kind, {}).get(EVENT_CONTEXT)
            if rule and getattr(rule, "mode", None) and rule.mode != "never":
                if "kept_by:retention_rule" not in tags:
                    tags.append("kept_by:retention_rule")
            if tags:
                meta["policy_tags"] = tags
                item["meta"] = meta


__all__ = [
    "apply_recall_policy_tags",
    "authority_for_source",
    "build_border_event",
    "build_conflict_event",
    "build_denied_event",
    "build_forget_event",
    "build_forget_events",
    "build_deleted_event",
    "build_deleted_events",
    "build_meta",
    "should_attempt_profile",
    "should_attempt_semantic",
    "with_policy_tags",
]
