from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.events import EVENT_RULE
from namel3ss.runtime.memory.helpers import authority_for_source, build_meta
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory_lanes.model import LANE_SYSTEM, LANE_TEAM, ensure_lane_meta
from namel3ss.runtime.memory_policy.model import AUTHORITY_SYSTEM
from namel3ss.runtime.memory_rules.model import (
    RULE_SCOPE_SYSTEM,
    RULE_SCOPE_TEAM,
    RULE_STATUS_ACTIVE,
    RULE_STATUS_PENDING,
    Rule,
    RuleSpec,
)
from namel3ss.runtime.memory_rules.parse import parse_rule_text
from namel3ss.runtime.memory.spaces import SPACE_PROJECT, SPACE_SYSTEM, SpaceContext
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta


@dataclass(frozen=True)
class RuleRequest:
    text: str
    scope: str
    priority: int
    requested_by: str


@dataclass(frozen=True)
class RulesSnapshotRequest:
    scope: str


def rule_request_from_state(state: Mapping[str, object] | None) -> RuleRequest | None:
    if not isinstance(state, Mapping):
        return None
    text = state.get("_memory_rule_text")
    if not text:
        return None
    scope_value = state.get("_memory_rule_scope") or RULE_SCOPE_TEAM
    scope = str(scope_value).strip().lower()
    if scope not in {RULE_SCOPE_TEAM, RULE_SCOPE_SYSTEM}:
        raise Namel3ssError("Rule scope must be team or system.")
    priority = _int_value(state.get("_memory_rule_priority"), default=0)
    requested_by = state.get("_memory_rule_by") or "user"
    return RuleRequest(text=str(text), scope=scope, priority=priority, requested_by=str(requested_by))


def rules_snapshot_request_from_state(state: Mapping[str, object] | None) -> RulesSnapshotRequest | None:
    if not isinstance(state, Mapping):
        return None
    scope_value = state.get("_memory_rules_snapshot")
    if not scope_value:
        return None
    scope = str(scope_value).strip().lower()
    if scope not in {RULE_SCOPE_TEAM, RULE_SCOPE_SYSTEM}:
        return None
    return RulesSnapshotRequest(scope=scope)


def build_rule_item(
    *,
    factory: MemoryItemFactory,
    store_key: str,
    text: str,
    source: str,
    scope: str,
    lane: str,
    space: str,
    owner: str,
    phase,
    status: str,
    priority: int,
    created_by: str,
) -> tuple[MemoryItem, RuleSpec]:
    spec = parse_rule_text(text)
    importance, reasons = importance_for_event(EVENT_RULE, text, source)
    authority, authority_reason = authority_for_source(source)
    rule_key = f"rule:{spec.rule_key}"
    meta = build_meta(
        EVENT_RULE,
        reasons,
        text,
        authority=authority,
        authority_reason=authority_reason,
        space=space,
        owner=owner,
        lane=lane,
        phase=phase,
        dedup_key=rule_key,
        promotion_target=space,
        promotion_reason="rule",
    )
    meta.update(
        {
            "rule": True,
            "rule_scope": scope,
            "rule_status": status,
            "rule_priority": int(priority),
            "rule_key": spec.rule_key,
            "rule_kind": spec.kind,
            "rule_actions": list(spec.actions),
            "rule_created_by": created_by,
        }
    )
    if spec.level:
        meta["rule_level"] = spec.level
    if spec.count is not None:
        meta["rule_count"] = int(spec.count)
    if spec.event_type:
        meta["rule_event_type"] = spec.event_type
    if lane == LANE_SYSTEM:
        meta["authority"] = AUTHORITY_SYSTEM
        meta["authority_reason"] = "rule:system"
        meta = ensure_lane_meta(meta, lane=lane, can_change=False)
    item = factory.create(
        session=store_key,
        kind=MemoryKind.SEMANTIC,
        text=text,
        source=source,
        importance=importance,
        meta=meta,
    )
    if status == RULE_STATUS_ACTIVE:
        item = _with_rule_status(item, status)
    return item, spec


def active_rules_for_store(items: Iterable[MemoryItem]) -> list[Rule]:
    rules = []
    for item in items:
        if not is_rule_item(item):
            continue
        if _rule_status(item) != RULE_STATUS_ACTIVE:
            continue
        rules.append(rule_from_item(item))
    rules.sort(key=lambda rule: (-int(rule.priority), rule.rule_id))
    return rules


def active_rules_for_scope(
    *,
    semantic: SemanticMemory,
    space_ctx: SpaceContext,
    scope: str,
) -> list[Rule]:
    store_key = space_ctx.store_key_for(rule_space_for_scope(scope), lane=rule_lane_for_scope(scope))
    return active_rules_for_store(semantic.items_for_store(store_key))


def pending_rules_from_proposals(proposals: Iterable, *, scope: str) -> list[Rule]:
    pending: list[Rule] = []
    for proposal in proposals:
        item = getattr(proposal, "memory_item", None)
        if item is None or not is_rule_item(item):
            continue
        if _rule_scope(item) != scope:
            continue
        pending.append(_rule_from_proposal(proposal))
    pending.sort(key=lambda rule: (-int(rule.priority), rule.rule_id))
    return pending


def replace_rules_for_key(
    *,
    items: Iterable[MemoryItem],
    rule_key: str,
) -> list[MemoryItem]:
    removed: list[MemoryItem] = []
    for item in items:
        if not is_rule_item(item):
            continue
        if item.meta.get("rule_key") == rule_key:
            removed.append(item)
    return removed


def rule_from_item(item: MemoryItem) -> Rule:
    meta = item.meta or {}
    return Rule(
        rule_id=item.id,
        text=item.text,
        scope=str(meta.get("rule_scope") or RULE_SCOPE_TEAM),
        lane=str(meta.get("lane") or LANE_TEAM),
        phase_id=str(meta.get("phase_id") or "phase-unknown"),
        status=str(meta.get("rule_status") or RULE_STATUS_ACTIVE),
        created_by=str(meta.get("rule_created_by") or item.source),
        created_at=int(item.created_at),
        priority=int(meta.get("rule_priority") or 0),
    )


def is_rule_item(item: MemoryItem | None) -> bool:
    if item is None:
        return False
    meta = item.meta or {}
    return bool(meta.get("rule"))


def rule_space_for_scope(scope: str) -> str:
    if scope == RULE_SCOPE_SYSTEM:
        return SPACE_SYSTEM
    return SPACE_PROJECT


def rule_lane_for_scope(scope: str) -> str:
    if scope == RULE_SCOPE_SYSTEM:
        return LANE_SYSTEM
    return LANE_TEAM


def apply_active_rule_meta(item: MemoryItem, *, phase) -> MemoryItem:
    meta = dict(item.meta)
    meta["rule_status"] = RULE_STATUS_ACTIVE
    meta = apply_phase_meta(meta, phase)
    return MemoryItem(
        id=item.id,
        kind=item.kind,
        text=item.text,
        source=item.source,
        created_at=item.created_at,
        importance=item.importance,
        scope=item.scope,
        meta=meta,
    )


def _rule_scope(item: MemoryItem) -> str:
    meta = item.meta or {}
    scope = meta.get("rule_scope")
    if isinstance(scope, str) and scope:
        return scope
    return RULE_SCOPE_TEAM


def _rule_status(item: MemoryItem) -> str:
    meta = item.meta or {}
    status = meta.get("rule_status")
    if isinstance(status, str) and status:
        return status
    return RULE_STATUS_ACTIVE


def _rule_from_proposal(proposal) -> Rule:
    item = proposal.memory_item
    meta = item.meta or {}
    return Rule(
        rule_id=item.id,
        text=item.text,
        scope=str(meta.get("rule_scope") or RULE_SCOPE_TEAM),
        lane=str(meta.get("lane") or LANE_TEAM),
        phase_id=str(proposal.phase_id or meta.get("phase_id") or "phase-unknown"),
        status=RULE_STATUS_PENDING,
        created_by=str(meta.get("rule_created_by") or proposal.proposed_by),
        created_at=int(item.created_at),
        priority=int(meta.get("rule_priority") or 0),
        proposal_id=str(proposal.proposal_id) if proposal.proposal_id else None,
    )


def _int_value(value: object, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _with_rule_status(item: MemoryItem, status: str) -> MemoryItem:
    meta = dict(item.meta)
    meta["rule_status"] = status
    return MemoryItem(
        id=item.id,
        kind=item.kind,
        text=item.text,
        source=item.source,
        created_at=item.created_at,
        importance=item.importance,
        scope=item.scope,
        meta=meta,
    )


__all__ = [
    "RuleRequest",
    "RulesSnapshotRequest",
    "active_rules_for_store",
    "active_rules_for_scope",
    "apply_active_rule_meta",
    "build_rule_item",
    "is_rule_item",
    "pending_rules_from_proposals",
    "replace_rules_for_key",
    "rule_from_item",
    "rule_lane_for_scope",
    "rule_request_from_state",
    "rule_space_for_scope",
    "rules_snapshot_request_from_state",
]
