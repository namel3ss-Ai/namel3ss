from __future__ import annotations

from dataclasses import dataclass, replace

from namel3ss.runtime.memory_budget.defaults import default_budget_configs
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_packs.format import MemoryOverrides, MemoryPack
from namel3ss.runtime.memory_packs.sources import (
    RuleSource,
    SourceMap,
    SourceTracker,
    SOURCE_OVERRIDE,
    pack_source,
)
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.model import LanePolicy, PhasePolicy
from namel3ss.runtime.memory_trust.model import TrustRules


@dataclass(frozen=True)
class AgreementDefaults:
    approval_count_required: int
    owner_override: bool


@dataclass(frozen=True)
class EffectiveMemoryPackSetup:
    rules: list[str]
    trust: TrustRules
    agreement: AgreementDefaults
    budgets: list[BudgetConfig]
    lanes: LanePolicy
    phase: PhasePolicy
    sources: SourceMap
    packs: list[MemoryPack]
    overrides: MemoryOverrides | None


def merge_packs(*, packs: list[MemoryPack], overrides: MemoryOverrides | None) -> EffectiveMemoryPackSetup:
    base_contract = default_contract(write_policy="normal", forget_policy="decay")
    rules: list[str] = []
    rule_sources: list[RuleSource] = []
    trust = base_contract.trust
    agreement = AgreementDefaults(
        approval_count_required=int(base_contract.trust.approval_count_required),
        owner_override=bool(base_contract.trust.owner_override),
    )
    budgets = list(default_budget_configs())
    lanes = base_contract.lanes
    phase = base_contract.phase
    tracker = SourceTracker()

    for pack in packs:
        source = pack_source(pack.pack_id)
        if pack.rules is not None:
            rules, rule_sources = _append_rules(
                rule_sources=rule_sources,
                new_rules=pack.rules,
                source=source,
            )
            tracker.apply_rules(rule_sources, source)
        if pack.trust is not None:
            trust, trust_fields = _apply_trust(trust, pack.trust)
            for field in trust_fields:
                tracker.apply_field(field, source)
        if pack.agreement is not None:
            agreement, agreement_fields = _apply_agreement(agreement, pack.agreement)
            for field in agreement_fields:
                tracker.apply_field(field, source)
        if pack.budgets is not None:
            budgets = _sorted_budgets(pack.budgets)
            tracker.apply_field("budgets", source)
        if pack.lanes is not None:
            lanes, lane_fields = _apply_lanes(lanes, pack.lanes)
            for field in lane_fields:
                tracker.apply_field(field, source)
        if pack.phase is not None:
            phase, phase_fields = _apply_phase(phase, pack.phase)
            for field in phase_fields:
                tracker.apply_field(field, source)

    if overrides is not None:
        source = SOURCE_OVERRIDE
        if overrides.rules is not None:
            rules, rule_sources = _append_rules(
                rule_sources=rule_sources,
                new_rules=overrides.rules,
                source=source,
            )
            tracker.apply_rules(rule_sources, source, is_override=True)
        if overrides.trust is not None:
            trust, trust_fields = _apply_trust(trust, overrides.trust)
            for field in trust_fields:
                tracker.apply_field(field, source, is_override=True)
        if overrides.agreement is not None:
            agreement, agreement_fields = _apply_agreement(agreement, overrides.agreement)
            for field in agreement_fields:
                tracker.apply_field(field, source, is_override=True)
        if overrides.budgets is not None:
            budgets = _sorted_budgets(overrides.budgets)
            tracker.apply_field("budgets", source, is_override=True)
        if overrides.lanes is not None:
            lanes, lane_fields = _apply_lanes(lanes, overrides.lanes)
            for field in lane_fields:
                tracker.apply_field(field, source, is_override=True)
        if overrides.phase is not None:
            phase, phase_fields = _apply_phase(phase, overrides.phase)
            for field in phase_fields:
                tracker.apply_field(field, source, is_override=True)

    return EffectiveMemoryPackSetup(
        rules=rules,
        trust=trust,
        agreement=agreement,
        budgets=budgets,
        lanes=lanes,
        phase=phase,
        sources=tracker.snapshot(),
        packs=list(packs),
        overrides=overrides,
    )


def _apply_trust(trust: TrustRules, pack) -> tuple[TrustRules, list[str]]:
    updates = {}
    fields: list[str] = []
    if pack.who_can_propose is not None:
        updates["who_can_propose"] = pack.who_can_propose
        fields.append("trust.who_can_propose")
    if pack.who_can_approve is not None:
        updates["who_can_approve"] = pack.who_can_approve
        fields.append("trust.who_can_approve")
    if pack.who_can_reject is not None:
        updates["who_can_reject"] = pack.who_can_reject
        fields.append("trust.who_can_reject")
    if pack.approval_count_required is not None:
        updates["approval_count_required"] = int(pack.approval_count_required)
        fields.append("trust.approval_count_required")
    if pack.owner_override is not None:
        updates["owner_override"] = bool(pack.owner_override)
        fields.append("trust.owner_override")
    if updates:
        trust = replace(trust, **updates)
    return trust, fields


def _apply_agreement(agreement: AgreementDefaults, pack) -> tuple[AgreementDefaults, list[str]]:
    fields: list[str] = []
    approval_count_required = agreement.approval_count_required
    owner_override = agreement.owner_override
    if pack.approval_count_required is not None:
        approval_count_required = int(pack.approval_count_required)
        fields.append("agreement.approval_count_required")
    if pack.owner_override is not None:
        owner_override = bool(pack.owner_override)
        fields.append("agreement.owner_override")
    return AgreementDefaults(
        approval_count_required=approval_count_required,
        owner_override=owner_override,
    ), fields


def _apply_lanes(lanes: LanePolicy, pack) -> tuple[LanePolicy, list[str]]:
    updates = {}
    fields: list[str] = []
    if pack.read_order is not None:
        updates["read_order"] = list(pack.read_order)
        fields.append("lanes.read_order")
    if pack.write_lanes is not None:
        updates["write_lanes"] = list(pack.write_lanes)
        fields.append("lanes.write_lanes")
    if pack.team_enabled is not None:
        updates["team_enabled"] = bool(pack.team_enabled)
        fields.append("lanes.team_enabled")
    if pack.system_enabled is not None:
        updates["system_enabled"] = bool(pack.system_enabled)
        fields.append("lanes.system_enabled")
    if pack.agent_enabled is not None:
        updates["agent_enabled"] = bool(pack.agent_enabled)
        fields.append("lanes.agent_enabled")
    if pack.team_event_types is not None:
        updates["team_event_types"] = list(pack.team_event_types)
        fields.append("lanes.team_event_types")
    if pack.team_can_change is not None:
        updates["team_can_change"] = bool(pack.team_can_change)
        fields.append("lanes.team_can_change")
    if updates:
        lanes = replace(lanes, **updates)
    return lanes, fields


def _apply_phase(phase: PhasePolicy, pack) -> tuple[PhasePolicy, list[str]]:
    updates = {}
    fields: list[str] = []
    if pack.enabled is not None:
        updates["enabled"] = bool(pack.enabled)
        fields.append("phase.enabled")
    if pack.mode is not None:
        updates["mode"] = str(pack.mode)
        fields.append("phase.mode")
    if pack.allow_cross_phase_recall is not None:
        updates["allow_cross_phase_recall"] = bool(pack.allow_cross_phase_recall)
        fields.append("phase.allow_cross_phase_recall")
    if pack.max_phases is not None:
        updates["max_phases"] = int(pack.max_phases)
        fields.append("phase.max_phases")
    if pack.diff_enabled is not None:
        updates["diff_enabled"] = bool(pack.diff_enabled)
        fields.append("phase.diff_enabled")
    if updates:
        phase = replace(phase, **updates)
    return phase, fields


def _sorted_budgets(budgets: list[BudgetConfig]) -> list[BudgetConfig]:
    return sorted(
        budgets,
        key=lambda cfg: (cfg.space, cfg.lane, cfg.phase, cfg.owner),
    )


def _append_rules(
    *,
    rule_sources: list[RuleSource],
    new_rules: list[str],
    source: str,
) -> tuple[list[str], list[RuleSource]]:
    entries = list(rule_sources)
    for text in new_rules:
        entries.append(RuleSource(text=str(text), source=source))
    entries = _dedupe_rules(entries)
    return [entry.text for entry in entries], entries


def _dedupe_rules(entries: list[RuleSource]) -> list[RuleSource]:
    seen: set[str] = set()
    deduped: list[RuleSource] = []
    for entry in reversed(entries):
        if entry.text in seen:
            continue
        seen.add(entry.text)
        deduped.append(entry)
    deduped.reverse()
    return deduped


__all__ = [
    "AgreementDefaults",
    "EffectiveMemoryPackSetup",
    "merge_packs",
]
