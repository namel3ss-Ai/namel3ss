from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_rules.model import (
    AppliedRule,
    Rule,
    RuleCheck,
    RULE_KIND_APPROVAL_COUNT,
    RULE_KIND_DENY_EVENT,
    RULE_KIND_MIN_LEVEL,
)
from namel3ss.runtime.memory_rules.parse import parse_rule_text
from namel3ss.runtime.memory_trust.model import TRUST_ORDER, TRUST_VIEWER


REASON_LEVEL_REQUIRED = "rule_level_required"
REASON_APPROVAL_COUNT = "rule_approval_count"
REASON_DENY_EVENT = "rule_denied_event_type"


def evaluate_rules(
    *,
    rules: list[Rule],
    action: str,
    actor_level: str | None,
    event_type: str | None = None,
) -> RuleCheck:
    applied: list[AppliedRule] = []
    required_level: str | None = None
    required_approvals: int | None = None
    allowed = True
    actor_level = actor_level or TRUST_VIEWER
    for rule in _ordered_rules(rules):
        spec = parse_rule_text(rule.text)
        if action not in spec.actions:
            continue
        rule_allowed = True
        reason = ""
        if spec.kind == RULE_KIND_MIN_LEVEL:
            reason = REASON_LEVEL_REQUIRED
            required_level = _max_level(required_level, spec.level)
            rule_allowed = _level_allows(actor_level, spec.level)
        elif spec.kind == RULE_KIND_APPROVAL_COUNT:
            reason = REASON_APPROVAL_COUNT
            if spec.count is not None:
                required_approvals = max(required_approvals or 0, spec.count)
        elif spec.kind == RULE_KIND_DENY_EVENT:
            reason = REASON_DENY_EVENT
            if spec.event_type and event_type == spec.event_type:
                rule_allowed = False
        else:
            raise Namel3ssError("Unknown rule kind.")
        applied.append(
            AppliedRule(
                rule_id=rule.rule_id,
                rule_text=rule.text,
                action=action,
                allowed=rule_allowed,
                reason=reason,
                priority=rule.priority,
                rule_key=spec.rule_key,
                required_level=spec.level,
                required_count=spec.count,
                event_type=spec.event_type,
            )
        )
        if not rule_allowed:
            allowed = False
    return RuleCheck(
        allowed=allowed,
        applied=applied,
        required_level=required_level,
        required_approvals=required_approvals,
    )


def _ordered_rules(rules: list[Rule]) -> list[Rule]:
    return sorted(rules, key=lambda rule: (-int(rule.priority), rule.rule_id))


def _level_allows(actor_level: str, required_level: str | None) -> bool:
    if not required_level:
        return True
    actor_rank = TRUST_ORDER.get(actor_level, -1)
    required_rank = TRUST_ORDER.get(required_level, -1)
    return actor_rank >= required_rank >= 0


def _max_level(current: str | None, candidate: str | None) -> str | None:
    if not candidate:
        return current
    if current is None:
        return candidate
    current_rank = TRUST_ORDER.get(current, -1)
    candidate_rank = TRUST_ORDER.get(candidate, -1)
    return candidate if candidate_rank > current_rank else current


__all__ = [
    "REASON_APPROVAL_COUNT",
    "REASON_DENY_EVENT",
    "REASON_LEVEL_REQUIRED",
    "evaluate_rules",
]
