from __future__ import annotations

from namel3ss.runtime.memory_budget.render import budget_title, budget_lines
from namel3ss.runtime.memory_budget.measure import BudgetUsage
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.traces.builders import build_memory_budget


def build_budget_event(
    *,
    ai_profile: str,
    session: str,
    usage: BudgetUsage,
    config: BudgetConfig,
) -> dict | None:
    lines = budget_lines(usage, config)
    if not lines:
        return None
    return build_memory_budget(
        ai_profile=ai_profile,
        session=session,
        space=usage.space,
        lane=usage.lane,
        phase_id=usage.phase_id,
        owner=usage.owner,
        title=budget_title(),
        lines=lines,
    )


__all__ = ["build_budget_event"]
