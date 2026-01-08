from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.events import EVENT_DECISION
from namel3ss.runtime.memory_links.model import LINK_TYPE_CONFLICTS_WITH
from namel3ss.runtime.memory_agreement.model import Proposal
from namel3ss.runtime.memory_rules.model import Rule


@dataclass(frozen=True)
class HandoffSelection:
    item_ids: list[str]
    summary_lines: list[str]
    decision_count: int
    proposal_count: int
    conflict_count: int
    rules_count: int
    impact_count: int
    groups: list["HandoffGroup"] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HandoffGroup:
    key: str
    item_ids: list[str]


def select_handoff_items(
    *,
    agent_items: list[MemoryItem],
    team_items: list[MemoryItem],
    proposals: list[Proposal],
    rules: list[Rule],
    max_items: int = 20,
) -> HandoffSelection:
    items = _ordered_items(agent_items + team_items)
    decisions = _select_by_event(items, EVENT_DECISION, limit=3)
    proposal_ids = _select_proposals(proposals, limit=3)
    conflicts = _select_conflicts(items, limit=3)
    rules_ids = _select_rules(rules, limit=5)
    impacts = _select_impact_warnings(items, limit=3)

    selected: list[str] = []
    seen: set[str] = set()
    for group in (decisions, proposal_ids, conflicts, rules_ids, impacts):
        for entry in group:
            if entry in seen:
                continue
            selected.append(entry)
            seen.add(entry)
            if len(selected) >= max_items:
                break
        if len(selected) >= max_items:
            break

    summary_lines = _summary_lines(
        decision_count=len(decisions),
        proposal_count=len(proposal_ids),
        conflict_count=len(conflicts),
        rules_count=len(rules_ids),
        impact_count=len(impacts),
    )
    groups = _build_groups(decisions, proposal_ids, conflicts, rules_ids, impacts)
    reasons = _build_reasons(groups)
    return HandoffSelection(
        item_ids=selected,
        summary_lines=summary_lines,
        decision_count=len(decisions),
        proposal_count=len(proposal_ids),
        conflict_count=len(conflicts),
        rules_count=len(rules_ids),
        impact_count=len(impacts),
        groups=groups,
        reasons=reasons,
    )


def _summary_lines(
    *,
    decision_count: int,
    proposal_count: int,
    conflict_count: int,
    rules_count: int,
    impact_count: int,
) -> list[str]:
    return [
        "Handoff packet summary.",
        f"Decision items count is {int(decision_count)}.",
        f"Pending proposals count is {int(proposal_count)}.",
        f"Conflicts count is {int(conflict_count)}.",
        f"Active rules count is {int(rules_count)}.",
        f"Impact warnings count is {int(impact_count)}.",
    ]


def _ordered_items(items: list[MemoryItem]) -> list[MemoryItem]:
    return sorted(items, key=lambda item: (-int(item.created_at), item.id))


def _select_by_event(items: list[MemoryItem], event_type: str, *, limit: int) -> list[str]:
    selected: list[str] = []
    for item in items:
        if item.meta.get("event_type") != event_type:
            continue
        selected.append(item.id)
        if len(selected) >= limit:
            break
    return selected


def _select_conflicts(items: list[MemoryItem], *, limit: int) -> list[str]:
    selected: list[str] = []
    for item in items:
        links = item.meta.get("links")
        if not isinstance(links, list):
            continue
        if not _has_conflict_link(links):
            continue
        selected.append(item.id)
        if len(selected) >= limit:
            break
    return selected


def _has_conflict_link(links: list[dict]) -> bool:
    for link in links:
        if isinstance(link, dict) and link.get("type") == LINK_TYPE_CONFLICTS_WITH:
            return True
    return False


def _select_proposals(proposals: list[Proposal], *, limit: int) -> list[str]:
    ordered = sorted(proposals, key=lambda proposal: (proposal.proposed_at, proposal.proposal_id))
    selected: list[str] = []
    for proposal in ordered:
        memory_id = proposal.memory_item.id if proposal.memory_item else None
        if memory_id:
            selected.append(memory_id)
        if len(selected) >= limit:
            break
    return selected


def _select_rules(rules: list[Rule], *, limit: int) -> list[str]:
    ordered = sorted(rules, key=lambda rule: (-int(rule.priority), rule.rule_id))
    return [rule.rule_id for rule in ordered[:limit]]


def _select_impact_warnings(items: list[MemoryItem], *, limit: int) -> list[str]:
    selected: list[str] = []
    for item in items:
        if not item.meta.get("impact_warning"):
            continue
        selected.append(item.id)
        if len(selected) >= limit:
            break
    return selected


def _build_groups(
    decisions: list[str],
    proposals: list[str],
    conflicts: list[str],
    rules: list[str],
    impacts: list[str],
) -> list[HandoffGroup]:
    groups: list[HandoffGroup] = []
    if decisions:
        groups.append(HandoffGroup(key="decisions", item_ids=list(decisions)))
    if proposals:
        groups.append(HandoffGroup(key="proposals", item_ids=list(proposals)))
    if conflicts:
        groups.append(HandoffGroup(key="conflicts", item_ids=list(conflicts)))
    if rules:
        groups.append(HandoffGroup(key="rules", item_ids=list(rules)))
    if impacts:
        groups.append(HandoffGroup(key="impact", item_ids=list(impacts)))
    return groups


def _build_reasons(groups: list[HandoffGroup]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for group in groups:
        for item_id in group.item_ids:
            reasons.setdefault(item_id, group.key)
    return reasons


__all__ = ["HandoffGroup", "HandoffSelection", "select_handoff_items"]
