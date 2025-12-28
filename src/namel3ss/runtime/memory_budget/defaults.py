from __future__ import annotations

from namel3ss.runtime.memory_budget.model import BUDGET_ANY, BudgetConfig
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM


DEFAULT_SHORT_TERM_LIMIT = 12
DEFAULT_SEMANTIC_LIMIT = 20
DEFAULT_PROFILE_LIMIT = 10
DEFAULT_TEAM_LIMIT = 30
DEFAULT_AGENT_LIMIT = 20
DEFAULT_LINK_LIMIT = 10
DEFAULT_PHASE_LIMIT = 6
DEFAULT_CACHE_MAX_ENTRIES = 50


def default_budget_configs() -> list[BudgetConfig]:
    base = BudgetConfig(
        space=BUDGET_ANY,
        lane=BUDGET_ANY,
        phase=BUDGET_ANY,
        owner=BUDGET_ANY,
        max_items_short_term=DEFAULT_SHORT_TERM_LIMIT,
        max_items_semantic=DEFAULT_SEMANTIC_LIMIT,
        max_items_profile=DEFAULT_PROFILE_LIMIT,
        max_links_per_item=DEFAULT_LINK_LIMIT,
        max_phases_per_lane=DEFAULT_PHASE_LIMIT,
        cache_enabled=True,
        cache_max_entries=DEFAULT_CACHE_MAX_ENTRIES,
        compaction_enabled=True,
    )
    team = BudgetConfig(
        space=BUDGET_ANY,
        lane=LANE_TEAM,
        phase=BUDGET_ANY,
        owner=BUDGET_ANY,
        max_items_team=DEFAULT_TEAM_LIMIT,
        max_links_per_item=DEFAULT_LINK_LIMIT,
        max_phases_per_lane=DEFAULT_PHASE_LIMIT,
        cache_enabled=True,
        cache_max_entries=DEFAULT_CACHE_MAX_ENTRIES,
        compaction_enabled=True,
    )
    agent = BudgetConfig(
        space=BUDGET_ANY,
        lane=LANE_AGENT,
        phase=BUDGET_ANY,
        owner=BUDGET_ANY,
        max_items_agent=DEFAULT_AGENT_LIMIT,
        max_links_per_item=DEFAULT_LINK_LIMIT,
        max_phases_per_lane=DEFAULT_PHASE_LIMIT,
        cache_enabled=True,
        cache_max_entries=DEFAULT_CACHE_MAX_ENTRIES,
        compaction_enabled=True,
    )
    return [team, agent, base]


__all__ = [
    "DEFAULT_AGENT_LIMIT",
    "DEFAULT_CACHE_MAX_ENTRIES",
    "DEFAULT_LINK_LIMIT",
    "DEFAULT_PHASE_LIMIT",
    "DEFAULT_PROFILE_LIMIT",
    "DEFAULT_SEMANTIC_LIMIT",
    "DEFAULT_SHORT_TERM_LIMIT",
    "DEFAULT_TEAM_LIMIT",
    "default_budget_configs",
]
