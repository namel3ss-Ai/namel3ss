from __future__ import annotations

from namel3ss.runtime.memory_rules.evaluate import (
    REASON_APPROVAL_COUNT,
    REASON_DENY_EVENT,
    REASON_LEVEL_REQUIRED,
)
from namel3ss.runtime.memory_rules.model import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_DELETE_TEAM_MEMORY,
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_CREATE,
    ACTION_HANDOFF_REJECT,
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    ACTION_PROMOTE_TO_TEAM_LANE,
    ACTION_PROPOSE_TEAM_MEMORY,
    ACTION_REJECT_TEAM_MEMORY,
    ACTION_WRITE_TEAM_LANE_DIRECT,
    AppliedRule,
    Rule,
)


def rule_applied_lines(applied: AppliedRule) -> list[str]:
    lines = [
        "Rule applied.",
        f"Rule id is {applied.rule_id}.",
        f"Rule text is {applied.rule_text}.",
        f"Action is {_action_line(applied.action)}.",
        "Allowed is yes." if applied.allowed else "Allowed is no.",
    ]
    reason_line = _reason_line(applied.reason)
    if reason_line:
        lines.append(reason_line)
    if applied.required_level:
        lines.append(f"Required level is {applied.required_level}.")
    if applied.required_count is not None:
        lines.append(f"Required approvals count is {int(applied.required_count)}.")
    if applied.event_type:
        lines.append(f"Blocked event type is {applied.event_type}.")
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


_ACTION_LINES = {
    ACTION_PROPOSE_TEAM_MEMORY: "propose team memory",
    ACTION_APPROVE_TEAM_MEMORY: "approve team memory",
    ACTION_REJECT_TEAM_MEMORY: "reject team memory",
    ACTION_PROMOTE_TO_TEAM_LANE: "promote memory to team lane",
    ACTION_PROMOTE_TO_SYSTEM_LANE: "promote memory to system lane",
    ACTION_WRITE_TEAM_LANE_DIRECT: "write memory to team lane",
    ACTION_DELETE_TEAM_MEMORY: "delete team memory",
    ACTION_HANDOFF_CREATE: "create handoff packet",
    ACTION_HANDOFF_APPLY: "apply handoff packet",
    ACTION_HANDOFF_REJECT: "reject handoff packet",
}


def _action_line(action: str) -> str:
    return _ACTION_LINES.get(action, action)


def _reason_line(reason: str | None) -> str | None:
    if reason == REASON_LEVEL_REQUIRED:
        return "Rule checks the trust level."
    if reason == REASON_APPROVAL_COUNT:
        return "Rule sets the approval count."
    if reason == REASON_DENY_EVENT:
        return "Rule blocks this event type."
    if reason:
        return f"Reason is {reason}."
    return None


__all__ = ["rule_applied_lines", "rule_changed_lines", "rules_snapshot_lines"]
