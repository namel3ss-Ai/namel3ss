from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, List, Tuple

from namel3ss.runtime.memory.contract import MemoryItem, MemoryKind
from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_FACT,
    EVENT_PREFERENCE,
)
from namel3ss.runtime.memory.facts import SENSITIVE_MARKERS
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_MY, LANE_SYSTEM, LANE_TEAM, lane_allowed_in_space
from namel3ss.runtime.memory_policy.model import (
    AUTHORITY_AI,
    AUTHORITY_SYSTEM,
    AUTHORITY_TOOL,
    AUTHORITY_USER,
    MemoryPolicyContract,
    PhasePolicy,
    SpacePromotionRule,
    RetentionRule,
    RETENTION_DECAY,
    RETENTION_NEVER,
    RETENTION_TTL,
)


DENY_EVENT_TYPE = "policy_deny_event_type"
DENY_LOW_SIGNAL = "policy_low_signal"
DENY_PROMOTION = "policy_deny_promotion"
DENY_PROFILE_KEY = "privacy_deny_profile_key"
DENY_PRIVACY_PATTERN = "privacy_deny_pattern"
DENY_PRIVACY_SENSITIVE = "privacy_deny_sensitive"
DENY_WRITE_POLICY = "write_policy_none"
DENY_WRITE_POLICY_MINIMAL = "write_policy_minimal"
DENY_WRITE_POLICY_CONTEXT = "write_policy_context"

BORDER_ALLOWED = "allowed"
BORDER_DENY_SPACE = "space_disabled"
BORDER_DENY_WRITE = "write_space_disallowed"
LANE_DENY_SPACE = "lane_space_disallowed"
LANE_DENY_TEAM = "lane_team_disabled"
LANE_DENY_SYSTEM = "lane_system_disabled"
LANE_DENY_AGENT = "lane_agent_disabled"
LANE_DENY_WRITE = "lane_write_disallowed"
LANE_DENY_EVENT = "lane_event_type"
LANE_DENY_SYSTEM_WRITE = "lane_system_read_only"
PROMOTION_DENY_EVENT_TYPE = "promotion_event_type"
PROMOTION_DENY_AUTHORITY = "promotion_authority"
PROMOTION_DENY_POLICY = "promotion_disallowed"
PHASE_DENY_DISABLED = "phase_disabled"
PHASE_DENY_DIFF = "phase_diff_disabled"


_WRITE_MINIMAL_TYPES = {EVENT_FACT, EVENT_PREFERENCE, EVENT_DECISION, EVENT_CORRECTION}

_SOURCE_AUTHORITY = {
    "user": AUTHORITY_USER,
    "ai": AUTHORITY_AI,
    "tool": AUTHORITY_TOOL,
    "system": AUTHORITY_SYSTEM,
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    tags: List[str]


@dataclass(frozen=True)
class ConflictDecision:
    winner: MemoryItem
    loser: MemoryItem
    rule: str


@dataclass(frozen=True)
class BorderDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    reason: str
    rule: str | None
    authority_used: str


@dataclass(frozen=True)
class PhaseDecision:
    allowed: bool
    reason: str


def evaluate_write(
    policy: MemoryPolicyContract,
    item: MemoryItem,
    *,
    event_type: str,
    low_signal: bool = False,
    privacy_text: str | None = None,
) -> PolicyDecision:
    kind = _kind_value(item.kind)
    tags: list[str] = []

    decision = _evaluate_privacy(policy, item, kind, tags, privacy_text=privacy_text)
    if not decision.allowed:
        return decision
    if policy.privacy.deny_patterns or policy.privacy.deny_sensitive:
        tags.append("allowed_by:privacy")

    if kind != MemoryKind.SHORT_TERM.value:
        decision = _evaluate_write_policy(policy.write_policy, kind, event_type, tags)
        if not decision.allowed:
            return decision

    if policy.allow_event_types and event_type not in policy.allow_event_types:
        return PolicyDecision(False, DENY_EVENT_TYPE, tags)
    if event_type in policy.deny_event_types:
        return PolicyDecision(False, DENY_EVENT_TYPE, tags)
    if policy.allow_event_types or policy.deny_event_types:
        tags.append("allowed_by:policy_event_types")

    promotion = policy.promotion.get(kind)
    if promotion and promotion.allowed_event_types and event_type not in promotion.allowed_event_types:
        return PolicyDecision(False, DENY_PROMOTION, tags)
    if promotion and promotion.allowed_event_types:
        tags.append("allowed_by:promotion_rule")

    if low_signal and kind in {MemoryKind.SEMANTIC.value, MemoryKind.PROFILE.value}:
        return PolicyDecision(False, DENY_LOW_SIGNAL, tags)

    return PolicyDecision(True, "allowed", tags)


def apply_retention(
    items: Iterable[MemoryItem],
    policy: MemoryPolicyContract,
    *,
    now_tick: int,
) -> tuple[list[MemoryItem], list[tuple[MemoryItem, str]]]:
    kept: list[MemoryItem] = []
    forgotten: list[tuple[MemoryItem, str]] = []
    for item in items:
        event_type = item.meta.get("event_type", EVENT_CONTEXT)
        rule = _retention_rule(policy, item.kind, event_type)
        if rule.mode == RETENTION_NEVER:
            kept.append(item)
            continue
        if rule.mode == RETENTION_TTL:
            expires_at = item.meta.get("expires_at")
            if expires_at is None and rule.ttl_ticks is not None:
                expires_at = item.created_at + rule.ttl_ticks
                item = _with_meta(item, {"expires_at": expires_at})
            if expires_at is not None and now_tick >= expires_at:
                forgotten.append((item, "ttl_expired"))
            else:
                kept.append(item)
            continue
        if rule.mode == RETENTION_DECAY:
            if rule.ttl_ticks is None:
                kept.append(item)
                continue
            age = max(now_tick - item.created_at, 0)
            if age > rule.ttl_ticks:
                forgotten.append((item, "decay"))
            else:
                kept.append(item)
            continue
        kept.append(item)
    return kept, forgotten


def evaluate_border_read(policy: MemoryPolicyContract, *, space: str) -> BorderDecision:
    if space not in policy.spaces.read_order:
        return BorderDecision(False, BORDER_DENY_SPACE)
    return BorderDecision(True, BORDER_ALLOWED)


def evaluate_border_write(policy: MemoryPolicyContract, *, space: str) -> BorderDecision:
    if space not in policy.spaces.write_spaces:
        return BorderDecision(False, BORDER_DENY_WRITE)
    return BorderDecision(True, BORDER_ALLOWED)


def evaluate_lane_read(policy: MemoryPolicyContract, *, lane: str, space: str) -> BorderDecision:
    if not lane_allowed_in_space(space, lane):
        return BorderDecision(False, LANE_DENY_SPACE)
    if lane == LANE_AGENT and not policy.lanes.agent_enabled:
        return BorderDecision(False, LANE_DENY_AGENT)
    if lane == LANE_TEAM and not policy.lanes.team_enabled:
        return BorderDecision(False, LANE_DENY_TEAM)
    if lane == LANE_SYSTEM and not policy.lanes.system_enabled:
        return BorderDecision(False, LANE_DENY_SYSTEM)
    return BorderDecision(True, BORDER_ALLOWED)


def evaluate_lane_write(policy: MemoryPolicyContract, *, lane: str, space: str) -> BorderDecision:
    if lane == LANE_SYSTEM:
        return BorderDecision(False, LANE_DENY_SYSTEM_WRITE)
    if not lane_allowed_in_space(space, lane):
        return BorderDecision(False, LANE_DENY_SPACE)
    if lane == LANE_AGENT and not policy.lanes.agent_enabled:
        return BorderDecision(False, LANE_DENY_AGENT)
    if lane not in policy.lanes.write_lanes:
        return BorderDecision(False, LANE_DENY_WRITE)
    return BorderDecision(True, BORDER_ALLOWED)


def evaluate_lane_promotion(
    policy: MemoryPolicyContract,
    *,
    lane: str,
    space: str,
    event_type: str,
) -> BorderDecision:
    if lane == LANE_SYSTEM:
        return BorderDecision(False, LANE_DENY_SYSTEM_WRITE)
    if lane == LANE_MY:
        if not lane_allowed_in_space(space, lane):
            return BorderDecision(False, LANE_DENY_SPACE)
        return BorderDecision(True, BORDER_ALLOWED)
    if lane == LANE_AGENT:
        if not lane_allowed_in_space(space, lane):
            return BorderDecision(False, LANE_DENY_SPACE)
        if not policy.lanes.agent_enabled:
            return BorderDecision(False, LANE_DENY_AGENT)
        return BorderDecision(True, BORDER_ALLOWED)
    if lane != LANE_TEAM:
        return BorderDecision(False, LANE_DENY_WRITE)
    if not lane_allowed_in_space(space, lane):
        return BorderDecision(False, LANE_DENY_SPACE)
    if not policy.lanes.team_enabled:
        return BorderDecision(False, LANE_DENY_TEAM)
    if policy.lanes.team_event_types and event_type not in policy.lanes.team_event_types:
        return BorderDecision(False, LANE_DENY_EVENT)
    return BorderDecision(True, BORDER_ALLOWED)


def evaluate_promotion(
    policy: MemoryPolicyContract,
    *,
    item: MemoryItem,
    from_space: str,
    to_space: str,
    event_type: str,
) -> PromotionDecision:
    authority = authority_for_item(item)
    rule = _find_promotion_rule(policy.spaces.promotions, from_space, to_space)
    if rule is None:
        return PromotionDecision(False, PROMOTION_DENY_POLICY, None, authority)
    if rule.allowed_event_types and event_type not in rule.allowed_event_types:
        return PromotionDecision(False, PROMOTION_DENY_EVENT_TYPE, "event_type", authority)
    required = rule.min_authority
    if rule.decision_override and event_type == EVENT_DECISION:
        required = AUTHORITY_USER
    if not authority_allows(authority, required, policy.authority_order):
        return PromotionDecision(False, PROMOTION_DENY_AUTHORITY, "authority", authority)
    return PromotionDecision(True, BORDER_ALLOWED, "allowed", authority)


def evaluate_phase_start(phase: PhasePolicy) -> PhaseDecision:
    if not phase.enabled:
        return PhaseDecision(False, PHASE_DENY_DISABLED)
    return PhaseDecision(True, BORDER_ALLOWED)


def evaluate_phase_diff(phase: PhasePolicy) -> PhaseDecision:
    if not phase.enabled:
        return PhaseDecision(False, PHASE_DENY_DISABLED)
    if not phase.diff_enabled:
        return PhaseDecision(False, PHASE_DENY_DIFF)
    return PhaseDecision(True, BORDER_ALLOWED)


def resolve_conflict(
    existing: MemoryItem,
    incoming: MemoryItem,
    authority_order: list[str],
) -> ConflictDecision:
    existing_rank = _authority_rank(authority_for_item(existing), authority_order)
    incoming_rank = _authority_rank(authority_for_item(incoming), authority_order)
    incoming_is_correction = _is_correction(incoming)
    existing_is_correction = _is_correction(existing)

    if existing_rank != incoming_rank and not _correction_override(incoming, existing, authority_order):
        if incoming_rank < existing_rank:
            return ConflictDecision(winner=incoming, loser=existing, rule="authority")
        return ConflictDecision(winner=existing, loser=incoming, rule="authority")

    if incoming_is_correction != existing_is_correction:
        if incoming_is_correction:
            return ConflictDecision(winner=incoming, loser=existing, rule="correction")
        return ConflictDecision(winner=existing, loser=incoming, rule="correction")

    if incoming.created_at != existing.created_at:
        if incoming.created_at > existing.created_at:
            return ConflictDecision(winner=incoming, loser=existing, rule="recency")
        return ConflictDecision(winner=existing, loser=incoming, rule="recency")

    if incoming.importance != existing.importance:
        if incoming.importance > existing.importance:
            return ConflictDecision(winner=incoming, loser=existing, rule="importance")
        return ConflictDecision(winner=existing, loser=incoming, rule="importance")

    if incoming.id > existing.id:
        return ConflictDecision(winner=incoming, loser=existing, rule="importance")
    return ConflictDecision(winner=existing, loser=incoming, rule="importance")


def authority_for_item(item: MemoryItem) -> str:
    authority = item.meta.get("authority")
    if isinstance(authority, str) and authority:
        return authority
    return _SOURCE_AUTHORITY.get(item.source, AUTHORITY_AI)


def authority_allows(authority: str, required: str, order: list[str]) -> bool:
    return _authority_rank(authority, order) <= _authority_rank(required, order)


def _kind_value(kind: MemoryKind | str) -> str:
    if isinstance(kind, MemoryKind):
        return kind.value
    return str(kind)


def _evaluate_write_policy(write_policy: str, kind: str, event_type: str, tags: list[str]) -> PolicyDecision:
    if write_policy == "none":
        return PolicyDecision(False, DENY_WRITE_POLICY, tags)
    if write_policy == "minimal" and event_type not in _WRITE_MINIMAL_TYPES:
        return PolicyDecision(False, DENY_WRITE_POLICY_MINIMAL, tags)
    if write_policy == "normal" and event_type == EVENT_CONTEXT and kind == MemoryKind.SEMANTIC.value:
        return PolicyDecision(False, DENY_WRITE_POLICY_CONTEXT, tags)
    tags.append(f"allowed_by:write_policy:{write_policy}")
    return PolicyDecision(True, "allowed", tags)


def _evaluate_privacy(
    policy: MemoryPolicyContract,
    item: MemoryItem,
    kind: str,
    tags: list[str],
    *,
    privacy_text: str | None = None,
) -> PolicyDecision:
    text = privacy_text if privacy_text is not None else item.text or ""
    lowered = text.lower()
    if policy.privacy.deny_sensitive and any(marker in lowered for marker in SENSITIVE_MARKERS):
        return PolicyDecision(False, DENY_PRIVACY_SENSITIVE, tags)
    if policy.privacy.deny_patterns:
        for pattern in policy.privacy.deny_patterns:
            if pattern and pattern.lower() in lowered:
                return PolicyDecision(False, DENY_PRIVACY_PATTERN, tags)
    if kind == MemoryKind.PROFILE.value and policy.privacy.allow_profile_keys:
        key = item.meta.get("key")
        if key not in policy.privacy.allow_profile_keys:
            return PolicyDecision(False, DENY_PROFILE_KEY, tags)
    return PolicyDecision(True, "allowed", tags)


def _retention_rule(policy: MemoryPolicyContract, kind: MemoryKind | str, event_type: str):
    kind_value = _kind_value(kind)
    rules = policy.retention.get(kind_value, {})
    return rules.get(event_type) or rules.get(EVENT_CONTEXT) or RetentionRule(mode=RETENTION_NEVER)


def _is_correction(item: MemoryItem) -> bool:
    return item.meta.get("event_type") == EVENT_CORRECTION


def _authority_rank(authority: str, order: list[str]) -> int:
    try:
        return order.index(authority)
    except ValueError:
        return len(order)


def _find_promotion_rule(
    rules: list[SpacePromotionRule],
    from_space: str,
    to_space: str,
) -> SpacePromotionRule | None:
    for rule in rules:
        if rule.from_space == from_space and rule.to_space == to_space:
            return rule
    return None


def _correction_override(incoming: MemoryItem, existing: MemoryItem, authority_order: list[str]) -> bool:
    if not _is_correction(incoming):
        return False
    incoming_rank = _authority_rank(authority_for_item(incoming), authority_order)
    required_rank = _authority_rank(AUTHORITY_USER, authority_order)
    if incoming_rank > required_rank:
        return False
    existing_rank = _authority_rank(authority_for_item(existing), authority_order)
    return incoming_rank >= required_rank and incoming_rank >= existing_rank


def _with_meta(item: MemoryItem, updates: dict) -> MemoryItem:
    meta = dict(item.meta)
    meta.update(updates)
    return replace(item, meta=meta)


__all__ = [
    "BorderDecision",
    "ConflictDecision",
    "PolicyDecision",
    "PromotionDecision",
    "PhaseDecision",
    "apply_retention",
    "authority_allows",
    "authority_for_item",
    "evaluate_border_read",
    "evaluate_border_write",
    "evaluate_lane_promotion",
    "evaluate_lane_read",
    "evaluate_lane_write",
    "evaluate_phase_diff",
    "evaluate_phase_start",
    "evaluate_promotion",
    "evaluate_write",
    "resolve_conflict",
    "BORDER_ALLOWED",
    "BORDER_DENY_SPACE",
    "BORDER_DENY_WRITE",
    "LANE_DENY_EVENT",
    "LANE_DENY_SPACE",
    "LANE_DENY_SYSTEM",
    "LANE_DENY_SYSTEM_WRITE",
    "LANE_DENY_TEAM",
    "LANE_DENY_WRITE",
    "DENY_EVENT_TYPE",
    "DENY_LOW_SIGNAL",
    "DENY_PROFILE_KEY",
    "DENY_PROMOTION",
    "DENY_PRIVACY_PATTERN",
    "DENY_PRIVACY_SENSITIVE",
    "DENY_WRITE_POLICY",
    "DENY_WRITE_POLICY_CONTEXT",
    "DENY_WRITE_POLICY_MINIMAL",
    "PHASE_DENY_DIFF",
    "PHASE_DENY_DISABLED",
    "PROMOTION_DENY_AUTHORITY",
    "PROMOTION_DENY_EVENT_TYPE",
    "PROMOTION_DENY_POLICY",
]
