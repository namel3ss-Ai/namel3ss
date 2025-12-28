from __future__ import annotations

from namel3ss.runtime.memory_rules.evaluate import evaluate_rules
from namel3ss.runtime.memory_rules.model import Rule, RuleCheck


def enforce_action(
    *,
    rules: list[Rule],
    action: str,
    actor_level: str | None,
    event_type: str | None = None,
) -> RuleCheck:
    return evaluate_rules(rules=rules, action=action, actor_level=actor_level, event_type=event_type)


def merge_required_approvals(base_required: int, rule_required: int | None) -> int:
    if rule_required is None:
        return base_required
    return max(int(base_required), int(rule_required))


__all__ = ["enforce_action", "merge_required_approvals"]
