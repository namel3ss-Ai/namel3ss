from __future__ import annotations

from typing import Dict, List

from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_EXECUTION,
    EVENT_FACT,
    EVENT_PREFERENCE,
    EVENT_RULE,
    EVENT_TYPES,
)
from namel3ss.runtime.memory.facts import FACT_KEYS, SENSITIVE_MARKERS
from namel3ss.runtime.memory.spaces import (
    SPACE_PROJECT,
    SPACE_SESSION,
    SPACE_SYSTEM,
    SPACE_USER,
)
from namel3ss.runtime.memory_policy.model import (
    AUTHORITY_AI,
    AUTHORITY_SYSTEM,
    AUTHORITY_TOOL,
    AUTHORITY_USER,
    LanePolicy,
    MemoryPolicyContract,
    PhasePolicy,
    PrivacyRule,
    PromotionRule,
    RetentionRule,
    RETENTION_DECAY,
    RETENTION_NEVER,
    RETENTION_TTL,
    SpacePolicy,
    SpacePromotionRule,
    TrustRules,
)
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_MY, LANE_SYSTEM, LANE_TEAM


DEFAULT_AUTHORITY_ORDER = [AUTHORITY_SYSTEM, AUTHORITY_TOOL, AUTHORITY_USER, AUTHORITY_AI]

DEFAULT_DECAY_LIMITS = {
    EVENT_CONTEXT: 12,
    EVENT_EXECUTION: 18,
    EVENT_DECISION: 40,
    EVENT_RULE: 40,
    EVENT_PREFERENCE: 40,
    EVENT_FACT: 60,
    EVENT_CORRECTION: 45,
}
DEFAULT_TTL_LIMIT = 25


def default_contract(*, write_policy: str, forget_policy: str, phase: PhasePolicy | None = None) -> MemoryPolicyContract:
    retention_mode = _retention_mode_for(forget_policy)
    retention = {
        "short_term": _retention_rules(RETENTION_NEVER),
        "semantic": _retention_rules(retention_mode),
        "profile": _retention_rules(RETENTION_NEVER),
    }
    promotion = {
        "short_term": PromotionRule(allowed_event_types=sorted(EVENT_TYPES)),
        "semantic": PromotionRule(allowed_event_types=sorted(EVENT_TYPES)),
        "profile": PromotionRule(allowed_event_types=[EVENT_FACT, EVENT_CORRECTION]),
    }
    privacy = PrivacyRule(
        deny_patterns=list(SENSITIVE_MARKERS),
        allow_profile_keys=list(FACT_KEYS),
        deny_sensitive=True,
    )
    space_rules = SpacePolicy(
        read_order=[SPACE_SESSION, SPACE_USER, SPACE_PROJECT, SPACE_SYSTEM],
        write_spaces=[SPACE_SESSION],
        promotions=[
            SpacePromotionRule(
                from_space=SPACE_SESSION,
                to_space=SPACE_USER,
                allowed_event_types=[EVENT_PREFERENCE, EVENT_DECISION, EVENT_FACT, EVENT_CORRECTION],
                min_authority=AUTHORITY_USER,
                decision_override=False,
            ),
            SpacePromotionRule(
                from_space=SPACE_SESSION,
                to_space=SPACE_PROJECT,
                allowed_event_types=[EVENT_PREFERENCE, EVENT_DECISION, EVENT_FACT, EVENT_CORRECTION],
                min_authority=AUTHORITY_TOOL,
                decision_override=True,
            ),
            SpacePromotionRule(
                from_space=SPACE_USER,
                to_space=SPACE_PROJECT,
                allowed_event_types=[EVENT_PREFERENCE, EVENT_DECISION, EVENT_FACT, EVENT_CORRECTION],
                min_authority=AUTHORITY_USER,
                decision_override=False,
            ),
        ],
    )
    phase_rules = phase or PhasePolicy(
        enabled=True,
        mode="current_only",
        allow_cross_phase_recall=False,
        max_phases=None,
        diff_enabled=True,
    )
    lane_rules = LanePolicy(
        read_order=[LANE_MY, LANE_AGENT, LANE_TEAM, LANE_SYSTEM],
        write_lanes=[LANE_MY, LANE_AGENT],
        team_enabled=True,
        system_enabled=True,
        agent_enabled=True,
        team_event_types=[EVENT_DECISION, EVENT_RULE, EVENT_EXECUTION],
        team_can_change=True,
    )
    return MemoryPolicyContract(
        write_policy=write_policy,
        allow_event_types=[],
        deny_event_types=[],
        retention=retention,
        promotion=promotion,
        privacy=privacy,
        authority_order=list(DEFAULT_AUTHORITY_ORDER),
        spaces=space_rules,
        phase=phase_rules,
        lanes=lane_rules,
        trust=TrustRules(),
    )


def _retention_mode_for(forget_policy: str) -> str:
    if forget_policy == "ttl":
        return RETENTION_TTL
    if forget_policy == "decay":
        return RETENTION_DECAY
    return RETENTION_NEVER


def _retention_rules(mode: str) -> Dict[str, RetentionRule]:
    rules: Dict[str, RetentionRule] = {}
    for event_type in sorted(EVENT_TYPES):
        if mode == RETENTION_NEVER:
            rules[event_type] = RetentionRule(mode=RETENTION_NEVER)
        elif mode == RETENTION_TTL:
            rules[event_type] = RetentionRule(mode=RETENTION_TTL, ttl_ticks=DEFAULT_TTL_LIMIT)
        else:
            limit = DEFAULT_DECAY_LIMITS.get(event_type, DEFAULT_DECAY_LIMITS[EVENT_CONTEXT])
            rules[event_type] = RetentionRule(mode=RETENTION_DECAY, ttl_ticks=limit)
    return rules


__all__ = [
    "DEFAULT_AUTHORITY_ORDER",
    "DEFAULT_DECAY_LIMITS",
    "DEFAULT_TTL_LIMIT",
    "default_contract",
]
