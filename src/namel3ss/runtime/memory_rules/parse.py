from __future__ import annotations

import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.events import EVENT_PREFERENCE
from namel3ss.runtime.memory_rules.model import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_CREATE,
    ACTION_HANDOFF_REJECT,
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    ACTION_PROMOTE_TO_TEAM_LANE,
    ACTION_PROPOSE_TEAM_MEMORY,
    ACTION_WRITE_TEAM_LANE_DIRECT,
    RULE_KIND_APPROVAL_COUNT,
    RULE_KIND_DENY_EVENT,
    RULE_KIND_MIN_LEVEL,
    RuleSpec,
)
from namel3ss.runtime.memory_trust.model import TRUST_LEVELS


_SUPPORTED_RULES = [
    "Only approvers can approve team proposals",
    "Only owners can change system memory",
    "Two approvals are needed for team changes",
    "Team memory cannot store personal preferences",
    "Only contributors can create handoff packets",
    "Only approvers can apply handoff packets",
    "Only owners can reject handoff packets",
]

_MIN_LEVEL_RULES = {
    "only approver can approve team proposals": ("approver", ACTION_APPROVE_TEAM_MEMORY),
    "only approvers can approve team proposals": ("approver", ACTION_APPROVE_TEAM_MEMORY),
    "only owner can change system memory": ("owner", ACTION_PROMOTE_TO_SYSTEM_LANE),
    "only owners can change system memory": ("owner", ACTION_PROMOTE_TO_SYSTEM_LANE),
    "only contributor can create handoff packets": ("contributor", ACTION_HANDOFF_CREATE),
    "only contributors can create handoff packets": ("contributor", ACTION_HANDOFF_CREATE),
    "only approver can apply handoff packets": ("approver", ACTION_HANDOFF_APPLY),
    "only approvers can apply handoff packets": ("approver", ACTION_HANDOFF_APPLY),
    "only owner can reject handoff packets": ("owner", ACTION_HANDOFF_REJECT),
    "only owners can reject handoff packets": ("owner", ACTION_HANDOFF_REJECT),
}

_APPROVAL_COUNT_RULES = {
    "two approvals are needed for team changes": 2,
}

_DENY_EVENT_RULES = {
    "team memory cannot store personal preferences": EVENT_PREFERENCE,
    "team memory cannot store preferences": EVENT_PREFERENCE,
}


def parse_rule_text(text: str) -> RuleSpec:
    if not isinstance(text, str) or not text.strip():
        raise Namel3ssError("Rule text is required.")
    normalized = _normalize_text(text)
    if normalized in _MIN_LEVEL_RULES:
        level, action = _MIN_LEVEL_RULES[normalized]
        if level not in TRUST_LEVELS:
            raise Namel3ssError("Rule uses an unknown trust level.")
        rule_key = f"min_level:{action}:{level}"
        return RuleSpec(kind=RULE_KIND_MIN_LEVEL, actions=[action], rule_key=rule_key, level=level)
    if normalized in _APPROVAL_COUNT_RULES:
        count = _APPROVAL_COUNT_RULES[normalized]
        rule_key = f"approval_count:team_changes:{count}"
        return RuleSpec(
            kind=RULE_KIND_APPROVAL_COUNT,
            actions=[ACTION_APPROVE_TEAM_MEMORY],
            rule_key=rule_key,
            count=count,
        )
    if normalized in _DENY_EVENT_RULES:
        event_type = _DENY_EVENT_RULES[normalized]
        rule_key = f"deny_event:team_memory:{event_type}"
        return RuleSpec(
            kind=RULE_KIND_DENY_EVENT,
            actions=[ACTION_PROPOSE_TEAM_MEMORY, ACTION_PROMOTE_TO_TEAM_LANE, ACTION_WRITE_TEAM_LANE_DIRECT],
            rule_key=rule_key,
            event_type=event_type,
        )
    raise Namel3ssError(
        "Unknown rule sentence. Supported rules are: " + "; ".join(_SUPPORTED_RULES) + "."
    )


def _normalize_text(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"\s+", " ", lowered)
    cleaned = re.sub(r"[.!?]+$", "", cleaned)
    return cleaned


__all__ = ["parse_rule_text"]
