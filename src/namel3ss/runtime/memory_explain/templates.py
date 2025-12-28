from __future__ import annotations

RECALL_REASON_LINES = {
    "matches_query": "it matches your question",
    "recency": "it is recent",
    "importance": "it is marked important",
    "active_rule": "it is active by rule",
}

DENIED_REASON_LINES = {
    "write_policy_none": "Policy blocks all memory writes.",
    "write_policy_minimal": "Policy allows only preference decision fact and correction.",
    "write_policy_context": "Policy blocks context writes.",
    "policy_deny_event_type": "Policy denies this event type.",
    "policy_low_signal": "Policy blocks low signal content.",
    "privacy_deny_profile_key": "Policy blocks this profile key.",
    "privacy_deny_pattern": "Policy blocks a privacy pattern.",
    "privacy_deny_sensitive": "Policy blocks sensitive content.",
}

DENIED_FIX_LINES = {
    "write_policy_none": "Enable memory writes in policy.",
    "write_policy_minimal": "Use a preference decision fact or correction.",
    "write_policy_context": "Use a preference decision fact or correction.",
    "policy_deny_event_type": "Use an allowed event type.",
    "policy_low_signal": "Provide more specific content.",
    "privacy_deny_profile_key": "Use an allowed profile key.",
    "privacy_deny_pattern": "Remove blocked patterns.",
    "privacy_deny_sensitive": "Remove secrets or tokens.",
}

DELETED_REASON_LINES = {
    "replaced": "Item was replaced by a newer one.",
    "conflict_loser": "Item lost a conflict.",
    "promoted": "Item was promoted to another space.",
    "expired": "Item expired by retention rules.",
    "cleanup": "Item was removed by cleanup.",
}

FORGET_REASON_LINES = {
    "ttl_expired": "Time to live expired.",
    "decay": "Item decayed by age.",
    "policy_cleanup": "Item was removed by policy cleanup.",
}

CONFLICT_RULE_LINES = {
    "authority": "Winner had higher authority.",
    "correction": "Winner was a correction.",
    "recency": "Winner was more recent.",
    "importance": "Winner was more important.",
}

RULE_ACTION_LINES = {
    "propose_team_memory": "propose team memory",
    "approve_team_memory": "approve team memory",
    "reject_team_memory": "reject team memory",
    "promote_to_team_lane": "promote memory to team lane",
    "promote_to_system_lane": "promote memory to system lane",
    "write_team_lane_direct": "write memory to team lane",
    "delete_team_memory": "delete team memory",
}

RULE_REASON_LINES = {
    "rule_level_required": "Rule needs a higher trust level.",
    "rule_approval_count": "Rule needs more approvals.",
    "rule_denied_event_type": "Rule blocks this event type.",
}


def recall_reason_line(reason: str) -> str | None:
    return RECALL_REASON_LINES.get(reason)


def denied_reason_line(reason: str) -> str | None:
    return DENIED_REASON_LINES.get(reason)


def denied_fix_line(reason: str) -> str | None:
    return DENIED_FIX_LINES.get(reason)


def deleted_reason_line(reason: str) -> str | None:
    return DELETED_REASON_LINES.get(reason)


def forget_reason_line(reason: str) -> str | None:
    return FORGET_REASON_LINES.get(reason)


def conflict_rule_line(rule: str) -> str | None:
    return CONFLICT_RULE_LINES.get(rule)


def rule_action_line(action: str) -> str | None:
    return RULE_ACTION_LINES.get(action)


def rule_reason_line(reason: str) -> str | None:
    return RULE_REASON_LINES.get(reason)


__all__ = [
    "conflict_rule_line",
    "deleted_reason_line",
    "denied_fix_line",
    "denied_reason_line",
    "forget_reason_line",
    "recall_reason_line",
    "rule_action_line",
    "rule_reason_line",
]
