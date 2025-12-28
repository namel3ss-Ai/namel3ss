from __future__ import annotations

from namel3ss.runtime.memory_rules.model import AppliedRule, Rule
from namel3ss.runtime.memory_rules.render import rule_applied_lines, rule_changed_lines, rules_snapshot_lines
from namel3ss.traces.builders import (
    build_memory_rule_applied,
    build_memory_rule_changed,
    build_memory_rules_snapshot,
)


def build_rule_applied_event(
    *,
    ai_profile: str,
    session: str,
    applied: AppliedRule,
) -> dict:
    return build_memory_rule_applied(
        ai_profile=ai_profile,
        session=session,
        rule_id=applied.rule_id,
        rule_text=applied.rule_text,
        action=applied.action,
        allowed=applied.allowed,
        reason=applied.reason,
        title="Memory rule applied",
        lines=rule_applied_lines(applied),
    )


def build_rules_snapshot_event(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_id: str,
    rules: list[Rule],
) -> dict:
    return build_memory_rules_snapshot(
        ai_profile=ai_profile,
        session=session,
        team_id=team_id,
        phase_id=phase_id,
        title="Memory rules snapshot",
        lines=rules_snapshot_lines(rules),
    )


def build_rule_changed_event(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    phase_from: str,
    phase_to: str,
    added: list[Rule],
    removed: list[Rule],
) -> dict:
    return build_memory_rule_changed(
        ai_profile=ai_profile,
        session=session,
        team_id=team_id,
        phase_from=phase_from,
        phase_to=phase_to,
        title="Memory rule changed",
        lines=rule_changed_lines(added, removed),
    )


__all__ = ["build_rule_applied_event", "build_rule_changed_event", "build_rules_snapshot_event"]
