from __future__ import annotations

SPACE_ORDER = ["session", "user", "project", "system"]
RECALL_REASON_ORDER = ["matches_query", "recency", "importance", "active_rule"]
CONFLICT_RULE_ORDER = ["authority", "correction", "recency", "importance"]
DELETE_REASON_ORDER = ["replaced", "conflict_loser", "promoted", "expired", "cleanup"]


def order_spaces(spaces: list[str]) -> list[str]:
    if not spaces:
        return []
    ranked = {space: idx for idx, space in enumerate(SPACE_ORDER)}
    return sorted(spaces, key=lambda space: (ranked.get(space, len(ranked)), space))


def order_recall_reasons(reasons: list[str]) -> list[str]:
    if not reasons:
        return []
    ranked = {reason: idx for idx, reason in enumerate(RECALL_REASON_ORDER)}
    return sorted(reasons, key=lambda reason: (ranked.get(reason, len(ranked)), reason))


def order_conflict_rules(rules: list[str]) -> list[str]:
    if not rules:
        return []
    ranked = {rule: idx for idx, rule in enumerate(CONFLICT_RULE_ORDER)}
    return sorted(rules, key=lambda rule: (ranked.get(rule, len(ranked)), rule))


def order_delete_reasons(reasons: list[str]) -> list[str]:
    if not reasons:
        return []
    ranked = {reason: idx for idx, reason in enumerate(DELETE_REASON_ORDER)}
    return sorted(reasons, key=lambda reason: (ranked.get(reason, len(ranked)), reason))


def order_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    if not counts:
        return []
    spaces = order_spaces(list(counts.keys()))
    return [(space, int(counts[space])) for space in spaces]


def order_phase_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    if not counts:
        return []
    return sorted(counts.items(), key=lambda item: (_phase_index(item[0]), item[0]))


def _phase_index(phase_id: str) -> int:
    if isinstance(phase_id, str) and phase_id.startswith("phase-"):
        suffix = phase_id.split("-", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return 0


__all__ = [
    "order_conflict_rules",
    "order_counts",
    "order_delete_reasons",
    "order_phase_counts",
    "order_recall_reasons",
    "order_spaces",
]
