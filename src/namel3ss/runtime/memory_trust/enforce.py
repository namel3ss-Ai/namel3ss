from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory_trust.model import TRUST_ORDER, TRUST_OWNER, TrustRules


REASON_ALLOWED = "allowed"
REASON_LEVEL_TOO_LOW = "level_too_low"
REASON_OWNER_OVERRIDE = "owner_override"


@dataclass(frozen=True)
class TrustDecision:
    action: str
    actor_level: str
    required_level: str
    allowed: bool
    reason: str


def can_propose(actor_level: str, rules: TrustRules) -> TrustDecision:
    required = rules.who_can_propose
    return _decision("propose", actor_level, required, owner_override=False)


def can_approve(actor_level: str, rules: TrustRules) -> TrustDecision:
    required = rules.who_can_approve
    return _decision("approve", actor_level, required, owner_override=rules.owner_override)


def can_reject(actor_level: str, rules: TrustRules) -> TrustDecision:
    required = rules.who_can_reject
    return _decision("reject", actor_level, required, owner_override=True)


def can_change_rules(actor_level: str, rules: TrustRules) -> TrustDecision:
    return _decision("change_rules", actor_level, TRUST_OWNER, owner_override=True)


def can_handoff_create(actor_level: str, rules: TrustRules) -> TrustDecision:
    required = rules.who_can_propose
    return _decision("handoff_create", actor_level, required, owner_override=False)


def can_handoff_apply(actor_level: str, rules: TrustRules) -> TrustDecision:
    required = rules.who_can_approve
    return _decision("handoff_apply", actor_level, required, owner_override=rules.owner_override)


def can_handoff_reject(actor_level: str, rules: TrustRules) -> TrustDecision:
    return _decision("handoff_reject", actor_level, TRUST_OWNER, owner_override=True)


def required_approvals(rules: TrustRules) -> int:
    return max(1, int(rules.approval_count_required))


def is_owner(actor_level: str) -> bool:
    return actor_level == TRUST_OWNER


def _decision(action: str, actor_level: str, required_level: str, *, owner_override: bool) -> TrustDecision:
    actor_rank = TRUST_ORDER.get(actor_level, -1)
    required_rank = TRUST_ORDER.get(required_level, -1)
    if owner_override and actor_level == TRUST_OWNER:
        return TrustDecision(
            action=action,
            actor_level=actor_level,
            required_level=required_level,
            allowed=True,
            reason=REASON_OWNER_OVERRIDE,
        )
    allowed = actor_rank >= required_rank >= 0
    reason = REASON_ALLOWED if allowed else REASON_LEVEL_TOO_LOW
    return TrustDecision(
        action=action,
        actor_level=actor_level,
        required_level=required_level,
        allowed=allowed,
        reason=reason,
    )


__all__ = [
    "REASON_ALLOWED",
    "REASON_LEVEL_TOO_LOW",
    "REASON_OWNER_OVERRIDE",
    "TrustDecision",
    "can_approve",
    "can_change_rules",
    "can_handoff_apply",
    "can_handoff_create",
    "can_handoff_reject",
    "can_propose",
    "can_reject",
    "is_owner",
    "required_approvals",
]
