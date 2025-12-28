from __future__ import annotations

from dataclasses import dataclass


BUDGET_ANY = "any"


@dataclass(frozen=True)
class BudgetConfig:
    space: str = BUDGET_ANY
    lane: str = BUDGET_ANY
    phase: str = BUDGET_ANY
    owner: str = BUDGET_ANY
    max_items_short_term: int | None = None
    max_items_semantic: int | None = None
    max_items_profile: int | None = None
    max_items_team: int | None = None
    max_items_agent: int | None = None
    max_links_per_item: int | None = None
    max_phases_per_lane: int | None = None
    cache_enabled: bool = True
    cache_max_entries: int = 100
    compaction_enabled: bool = True

    def matches(self, *, space: str, lane: str, phase: str, owner: str) -> bool:
        if not _scope_match(self.space, space):
            return False
        if not _scope_match(self.lane, lane):
            return False
        if not _scope_match(self.phase, phase):
            return False
        if not _scope_match(self.owner, owner):
            return False
        return True

    def specificity(self) -> int:
        score = 0
        for value in (self.space, self.lane, self.phase, self.owner):
            if value != BUDGET_ANY:
                score += 1
        return score


def select_budget(
    configs: list[BudgetConfig],
    *,
    space: str,
    lane: str,
    phase: str,
    owner: str,
) -> BudgetConfig | None:
    matches = [cfg for cfg in configs if cfg.matches(space=space, lane=lane, phase=phase, owner=owner)]
    if not matches:
        return None
    matches.sort(key=lambda cfg: (-cfg.specificity(), cfg.space, cfg.lane, cfg.phase, cfg.owner))
    return matches[0]


def _scope_match(expected: str, actual: str) -> bool:
    if expected == BUDGET_ANY:
        return True
    return expected == actual


__all__ = ["BUDGET_ANY", "BudgetConfig", "select_budget"]
