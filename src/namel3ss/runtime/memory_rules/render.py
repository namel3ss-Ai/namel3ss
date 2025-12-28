from __future__ import annotations

from namel3ss.runtime.memory_rules.model import AppliedRule, Rule


def rule_applied_lines(applied: AppliedRule) -> list[str]:
    lines = [
        "Rule applied.",
        f"Rule id is {applied.rule_id}.",
        f"Rule text is {applied.rule_text}.",
        f"Action is {applied.action}.",
        "Allowed is yes." if applied.allowed else "Allowed is no.",
    ]
    if applied.reason:
        lines.append(f"Reason is {applied.reason}.")
    return lines


def rules_snapshot_lines(rules: list[Rule]) -> list[str]:
    if not rules:
        return ["No active rules."]
    lines: list[str] = []
    for rule in _ordered_rules(rules):
        lines.append(rule.text)
    return lines


def rule_changed_lines(added: list[Rule], removed: list[Rule]) -> list[str]:
    lines: list[str] = []
    for rule in _ordered_rules(added):
        lines.append(f"Rule added: {rule.text}.")
    for rule in _ordered_rules(removed):
        lines.append(f"Rule removed: {rule.text}.")
    if not lines:
        lines.append("No rule changes.")
    return lines


def _ordered_rules(rules: list[Rule]) -> list[Rule]:
    return sorted(rules, key=lambda rule: (-int(rule.priority), rule.rule_id))


__all__ = ["rule_applied_lines", "rule_changed_lines", "rules_snapshot_lines"]
