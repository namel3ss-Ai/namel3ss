from __future__ import annotations

from dataclasses import dataclass


RULE_SCOPE_TEAM = "team"
RULE_SCOPE_SYSTEM = "system"
RULE_SCOPES = {RULE_SCOPE_TEAM, RULE_SCOPE_SYSTEM}

RULE_STATUS_ACTIVE = "active"
RULE_STATUS_PENDING = "pending"
RULE_STATUSES = {RULE_STATUS_ACTIVE, RULE_STATUS_PENDING}

RULE_KIND_MIN_LEVEL = "min_level"
RULE_KIND_APPROVAL_COUNT = "approval_count"
RULE_KIND_DENY_EVENT = "deny_event"
RULE_KINDS = {RULE_KIND_MIN_LEVEL, RULE_KIND_APPROVAL_COUNT, RULE_KIND_DENY_EVENT}

ACTION_PROPOSE_TEAM_MEMORY = "propose_team_memory"
ACTION_APPROVE_TEAM_MEMORY = "approve_team_memory"
ACTION_REJECT_TEAM_MEMORY = "reject_team_memory"
ACTION_PROMOTE_TO_TEAM_LANE = "promote_to_team_lane"
ACTION_PROMOTE_TO_SYSTEM_LANE = "promote_to_system_lane"
ACTION_WRITE_TEAM_LANE_DIRECT = "write_team_lane_direct"
ACTION_DELETE_TEAM_MEMORY = "delete_team_memory"
ACTION_HANDOFF_CREATE = "handoff_create"
ACTION_HANDOFF_APPLY = "handoff_apply"
ACTION_HANDOFF_REJECT = "handoff_reject"
RULE_ACTIONS = {
    ACTION_PROPOSE_TEAM_MEMORY,
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_REJECT_TEAM_MEMORY,
    ACTION_PROMOTE_TO_TEAM_LANE,
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    ACTION_WRITE_TEAM_LANE_DIRECT,
    ACTION_DELETE_TEAM_MEMORY,
    ACTION_HANDOFF_CREATE,
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_REJECT,
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    text: str
    scope: str
    lane: str
    phase_id: str
    status: str
    created_by: str
    created_at: int
    priority: int = 0
    proposal_id: str | None = None


@dataclass(frozen=True)
class RuleSpec:
    kind: str
    actions: list[str]
    rule_key: str
    level: str | None = None
    count: int | None = None
    event_type: str | None = None


@dataclass(frozen=True)
class AppliedRule:
    rule_id: str
    rule_text: str
    action: str
    allowed: bool
    reason: str
    priority: int
    rule_key: str
    required_level: str | None = None
    required_count: int | None = None
    event_type: str | None = None


@dataclass(frozen=True)
class RuleCheck:
    allowed: bool
    applied: list[AppliedRule]
    required_level: str | None = None
    required_approvals: int | None = None


__all__ = [
    "ACTION_APPROVE_TEAM_MEMORY",
    "ACTION_DELETE_TEAM_MEMORY",
    "ACTION_HANDOFF_APPLY",
    "ACTION_HANDOFF_CREATE",
    "ACTION_HANDOFF_REJECT",
    "ACTION_PROMOTE_TO_SYSTEM_LANE",
    "ACTION_PROMOTE_TO_TEAM_LANE",
    "ACTION_PROPOSE_TEAM_MEMORY",
    "ACTION_REJECT_TEAM_MEMORY",
    "ACTION_WRITE_TEAM_LANE_DIRECT",
    "AppliedRule",
    "Rule",
    "RuleCheck",
    "RULE_ACTIONS",
    "RULE_KIND_APPROVAL_COUNT",
    "RULE_KIND_DENY_EVENT",
    "RULE_KIND_MIN_LEVEL",
    "RULE_KINDS",
    "RULE_SCOPE_SYSTEM",
    "RULE_SCOPE_TEAM",
    "RULE_SCOPES",
    "RULE_STATUS_ACTIVE",
    "RULE_STATUS_PENDING",
    "RULE_STATUSES",
    "RuleSpec",
]
