from __future__ import annotations

from dataclasses import dataclass


SOURCE_DEFAULT = "default"
SOURCE_OVERRIDE = "local override"


@dataclass(frozen=True)
class RuleSource:
    text: str
    source: str


@dataclass(frozen=True)
class OverrideEntry:
    field: str
    from_source: str
    to_source: str


@dataclass(frozen=True)
class SourceMap:
    field_sources: dict[str, str]
    rule_sources: list[RuleSource]
    overrides: list[OverrideEntry]


class SourceTracker:
    def __init__(self) -> None:
        self._field_sources = {name: SOURCE_DEFAULT for name in _field_names()}
        self._rule_sources: list[RuleSource] = []
        self._overrides: list[OverrideEntry] = []

    def apply_field(self, field: str, source: str, *, is_override: bool = False) -> None:
        previous = self._field_sources.get(field, SOURCE_DEFAULT)
        self._field_sources[field] = source
        if is_override and previous != source:
            self._overrides.append(OverrideEntry(field=field, from_source=previous, to_source=source))

    def apply_rules(self, rule_sources: list[RuleSource], source: str, *, is_override: bool = False) -> None:
        self.apply_field("rules", source, is_override=is_override)
        self._rule_sources = list(rule_sources)

    def snapshot(self) -> SourceMap:
        return SourceMap(
            field_sources=dict(self._field_sources),
            rule_sources=list(self._rule_sources),
            overrides=list(self._overrides),
        )


def pack_source(pack_id: str) -> str:
    return f"pack {pack_id}"


def _field_names() -> list[str]:
    return [
        "rules",
        "trust.who_can_propose",
        "trust.who_can_approve",
        "trust.who_can_reject",
        "trust.approval_count_required",
        "trust.owner_override",
        "agreement.approval_count_required",
        "agreement.owner_override",
        "budgets",
        "lanes.read_order",
        "lanes.write_lanes",
        "lanes.team_enabled",
        "lanes.system_enabled",
        "lanes.agent_enabled",
        "lanes.team_event_types",
        "lanes.team_can_change",
        "phase.enabled",
        "phase.mode",
        "phase.allow_cross_phase_recall",
        "phase.max_phases",
        "phase.diff_enabled",
    ]


__all__ = [
    "OverrideEntry",
    "RuleSource",
    "SourceMap",
    "SourceTracker",
    "SOURCE_DEFAULT",
    "SOURCE_OVERRIDE",
    "pack_source",
]
