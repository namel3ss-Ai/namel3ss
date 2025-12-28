from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory_budget.measure import BudgetUsage
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM


ACTION_ALLOW = "allow"
ACTION_COMPACT = "compact"
ACTION_DELETE_LOW_VALUE = "delete_low_value"
ACTION_DENY_WRITE = "deny_write"

REASON_SHORT_TERM_LIMIT = "short_term_limit"
REASON_SEMANTIC_LIMIT = "semantic_limit"
REASON_PROFILE_LIMIT = "profile_limit"
REASON_TEAM_LIMIT = "team_limit"
REASON_AGENT_LIMIT = "agent_limit"
REASON_PHASE_LIMIT = "phase_limit"


@dataclass(frozen=True)
class BudgetDecision:
    action: str
    reason: str
    target: str
    limit: int | None
    current: int
    incoming: int
    projected: int
    over_by: int


def enforce_budget(
    *,
    config: BudgetConfig,
    usage: BudgetUsage,
    kind: str,
    incoming: int = 0,
) -> BudgetDecision:
    checks = _build_checks(config, usage, kind=kind, incoming=incoming)
    for check in checks:
        if check["limit"] is None:
            continue
        projected = check["current"] + check["incoming"]
        if projected <= check["limit"]:
            continue
        over_by = projected - check["limit"]
        action = _select_action(config)
        return BudgetDecision(
            action=action,
            reason=check["reason"],
            target=check["target"],
            limit=check["limit"],
            current=check["current"],
            incoming=check["incoming"],
            projected=projected,
            over_by=over_by,
        )
    return BudgetDecision(
        action=ACTION_ALLOW,
        reason="",
        target=kind,
        limit=None,
        current=_current_for_kind(usage, kind),
        incoming=incoming,
        projected=_current_for_kind(usage, kind) + incoming,
        over_by=0,
    )


def _build_checks(config: BudgetConfig, usage: BudgetUsage, *, kind: str, incoming: int) -> list[dict]:
    checks: list[dict] = []
    kind_limit, kind_reason = _kind_limit(config, kind)
    checks.append(
        {
            "target": kind,
            "reason": kind_reason,
            "limit": kind_limit,
            "current": _current_for_kind(usage, kind),
            "incoming": incoming,
        }
    )
    if usage.lane == LANE_TEAM:
        checks.append(
            {
                "target": "team",
                "reason": REASON_TEAM_LIMIT,
                "limit": config.max_items_team,
                "current": usage.total_count,
                "incoming": incoming,
            }
        )
    if usage.lane == LANE_AGENT:
        checks.append(
            {
                "target": "agent",
                "reason": REASON_AGENT_LIMIT,
                "limit": config.max_items_agent,
                "current": usage.total_count,
                "incoming": incoming,
            }
        )
    checks.append(
        {
            "target": "phase",
            "reason": REASON_PHASE_LIMIT,
            "limit": config.max_phases_per_lane,
            "current": usage.phase_count,
            "incoming": 0,
        }
    )
    return checks


def _kind_limit(config: BudgetConfig, kind: str) -> tuple[int | None, str]:
    if kind == "short_term":
        return config.max_items_short_term, REASON_SHORT_TERM_LIMIT
    if kind == "semantic":
        return config.max_items_semantic, REASON_SEMANTIC_LIMIT
    if kind == "profile":
        return config.max_items_profile, REASON_PROFILE_LIMIT
    return None, ""


def _current_for_kind(usage: BudgetUsage, kind: str) -> int:
    if kind == "short_term":
        return usage.short_term_count
    if kind == "semantic":
        return usage.semantic_count
    if kind == "profile":
        return usage.profile_count
    return usage.total_count


def _select_action(config: BudgetConfig) -> str:
    if config.compaction_enabled:
        return ACTION_COMPACT
    return ACTION_DELETE_LOW_VALUE


__all__ = [
    "ACTION_ALLOW",
    "ACTION_COMPACT",
    "ACTION_DELETE_LOW_VALUE",
    "ACTION_DENY_WRITE",
    "REASON_AGENT_LIMIT",
    "REASON_PHASE_LIMIT",
    "REASON_PROFILE_LIMIT",
    "REASON_SEMANTIC_LIMIT",
    "REASON_SHORT_TERM_LIMIT",
    "REASON_TEAM_LIMIT",
    "BudgetDecision",
    "enforce_budget",
]
