from __future__ import annotations

from namel3ss.runtime.memory_budget.measure import BudgetUsage
from namel3ss.runtime.memory_budget.model import BudgetConfig


NEAR_LIMIT_RATIO = 0.8


def budget_title() -> str:
    return "Memory budget"


def budget_lines(usage: BudgetUsage, config: BudgetConfig) -> list[str]:
    lines: list[str] = []
    lines.extend(_usage_lines("Short term", usage.short_term_count, config.max_items_short_term))
    lines.extend(_usage_lines("Semantic", usage.semantic_count, config.max_items_semantic))
    lines.extend(_usage_lines("Profile", usage.profile_count, config.max_items_profile))
    if usage.lane == "team":
        lines.extend(_usage_lines("Team", usage.total_count, config.max_items_team))
    if usage.lane == "agent":
        lines.extend(_usage_lines("Agent", usage.total_count, config.max_items_agent))
    lines.extend(
        _usage_lines("Phase count", usage.phase_count, config.max_phases_per_lane, noun="phases", include_memory=False)
    )
    return lines


def _usage_lines(
    label: str,
    current: int,
    limit: int | None,
    *,
    noun: str = "items",
    include_memory: bool = True,
) -> list[str]:
    if limit is None or limit <= 0:
        return []
    if current <= 0:
        return []
    ratio = current / limit
    if ratio < NEAR_LIMIT_RATIO:
        return []
    state = "near" if current < limit else "over"
    if include_memory:
        lines = [f"{label} memory is {state} its limit."]
    else:
        lines = [f"{label} is {state} its limit."]
    lines.append(f"{label} {noun} are {current} of {limit}.")
    return lines


__all__ = ["NEAR_LIMIT_RATIO", "budget_lines", "budget_title"]
