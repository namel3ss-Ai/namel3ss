from __future__ import annotations

from namel3ss.runtime.memory_trust.render import (
    approval_recorded_lines,
    trust_check_lines,
    trust_check_title,
    trust_rules_lines,
    trust_rules_title,
)
from namel3ss.runtime.memory_trust.model import TrustRules
from namel3ss.traces.builders import (
    build_memory_approval_recorded,
    build_memory_trust_check,
    build_memory_trust_rules,
)


def build_trust_check_event(
    *,
    ai_profile: str,
    session: str,
    action: str,
    actor_id: str,
    actor_level: str,
    required_level: str,
    allowed: bool,
    reason: str,
) -> dict:
    return build_memory_trust_check(
        ai_profile=ai_profile,
        session=session,
        action=action,
        actor_id=actor_id,
        actor_level=actor_level,
        required_level=required_level,
        allowed=allowed,
        reason=reason,
        title=trust_check_title(action),
        lines=trust_check_lines(
            action=action,
            actor_id=actor_id,
            actor_level=actor_level,
            required_level=required_level,
            allowed=allowed,
            reason=reason,
        ),
    )


def build_approval_recorded_event(
    *,
    ai_profile: str,
    session: str,
    proposal_id: str,
    actor_id: str,
    count_now: int,
    count_required: int,
) -> dict:
    return build_memory_approval_recorded(
        ai_profile=ai_profile,
        session=session,
        proposal_id=proposal_id,
        actor_id=actor_id,
        count_now=count_now,
        count_required=count_required,
        title="Team approval recorded",
        lines=approval_recorded_lines(
            proposal_id=proposal_id,
            actor_id=actor_id,
            count_now=count_now,
            count_required=count_required,
        ),
    )


def build_trust_rules_event(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    rules: TrustRules,
) -> dict:
    return build_memory_trust_rules(
        ai_profile=ai_profile,
        session=session,
        team_id=team_id,
        title=trust_rules_title(),
        lines=trust_rules_lines(rules),
    )


__all__ = [
    "build_approval_recorded_event",
    "build_trust_check_event",
    "build_trust_rules_event",
]
