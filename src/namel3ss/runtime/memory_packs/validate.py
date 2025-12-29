from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.events import EVENT_TYPES
from namel3ss.runtime.memory_budget.model import BUDGET_ANY, BudgetConfig
from namel3ss.runtime.memory_lanes.model import LANES
from namel3ss.runtime.memory_packs.format import (
    MEMORY_PACK_VERSION,
    MemoryOverrides,
    MemoryPack,
    PackAgreementSettings,
    PackLaneDefaults,
    PackPhaseDefaults,
    PackTrustSettings,
)
from namel3ss.runtime.memory_rules.parse import parse_rule_text
from namel3ss.runtime.memory_trust.model import TRUST_LEVELS


_ALLOWED_PACK_KEYS = {
    "format_version",
    "pack_id",
    "pack_name",
    "pack_version",
    "rules",
    "trust",
    "agreement",
    "budgets",
    "lanes",
    "phase",
}

_ALLOWED_OVERRIDE_KEYS = {
    "rules",
    "trust",
    "agreement",
    "budgets",
    "lanes",
    "phase",
}

_ALLOWED_BUDGET_KEYS = {
    "space",
    "lane",
    "phase",
    "owner",
    "max_items_short_term",
    "max_items_semantic",
    "max_items_profile",
    "max_items_team",
    "max_items_agent",
    "max_links_per_item",
    "max_phases_per_lane",
    "cache_enabled",
    "cache_max_entries",
    "compaction_enabled",
}

_ALLOWED_TRUST_KEYS = {
    "who_can_propose",
    "who_can_approve",
    "who_can_reject",
    "approval_count_required",
    "owner_override",
}

_ALLOWED_AGREEMENT_KEYS = {
    "approval_count_required",
    "owner_override",
}

_ALLOWED_LANE_KEYS = {
    "read_order",
    "write_lanes",
    "team_enabled",
    "system_enabled",
    "agent_enabled",
    "team_event_types",
    "team_can_change",
}

_ALLOWED_PHASE_KEYS = {
    "enabled",
    "mode",
    "allow_cross_phase_recall",
    "max_phases",
    "diff_enabled",
}


def validate_pack_payload(payload: dict, *, rules: list[str] | None, source_path: str) -> MemoryPack:
    data = _require_mapping(payload, "pack")
    _reject_unknown_keys(data, _ALLOWED_PACK_KEYS, source_path)
    format_version = _required_str(data.get("format_version"), "format_version", source_path)
    if format_version != MEMORY_PACK_VERSION:
        raise Namel3ssError("Memory pack format version does not match.")
    pack_id = _required_str(data.get("pack_id"), "pack_id", source_path)
    pack_name = _required_str(data.get("pack_name"), "pack_name", source_path)
    pack_version = _required_str(data.get("pack_version"), "pack_version", source_path)
    pack_rules = _parse_rules(data.get("rules"), rules, source_path)
    trust = _parse_trust(data.get("trust"), source_path)
    agreement = _parse_agreement(data.get("agreement"), source_path)
    budgets = _parse_budgets(data.get("budgets"), source_path)
    lanes = _parse_lanes(data.get("lanes"), source_path)
    phase = _parse_phase(data.get("phase"), source_path)
    return MemoryPack(
        pack_id=pack_id,
        pack_name=pack_name,
        pack_version=pack_version,
        rules=pack_rules,
        trust=trust,
        agreement=agreement,
        budgets=budgets,
        lanes=lanes,
        phase=phase,
        source_path=source_path,
    )


def validate_overrides_payload(payload: dict, *, source_path: str) -> MemoryOverrides:
    data = _require_mapping(payload, "overrides")
    _reject_unknown_keys(data, _ALLOWED_OVERRIDE_KEYS, source_path)
    rules = _parse_rules(data.get("rules"), None, source_path, allow_missing=True)
    trust = _parse_trust(data.get("trust"), source_path)
    agreement = _parse_agreement(data.get("agreement"), source_path)
    budgets = _parse_budgets(data.get("budgets"), source_path)
    lanes = _parse_lanes(data.get("lanes"), source_path)
    phase = _parse_phase(data.get("phase"), source_path)
    return MemoryOverrides(
        rules=rules,
        trust=trust,
        agreement=agreement,
        budgets=budgets,
        lanes=lanes,
        phase=phase,
        source_path=source_path,
    )


def _parse_rules(
    rules_value: object,
    file_rules: list[str] | None,
    source_path: str,
    *,
    allow_missing: bool = False,
) -> list[str] | None:
    if rules_value is None and file_rules is None:
        return None if allow_missing else None
    rules = []
    if rules_value is not None:
        if not isinstance(rules_value, list):
            raise Namel3ssError("Memory pack rules must be a list of sentences.")
        rules = [str(entry).strip() for entry in rules_value if str(entry).strip()]
    elif file_rules is not None:
        rules = [str(entry).strip() for entry in file_rules if str(entry).strip()]
    for rule in rules:
        parse_rule_text(rule)
    return rules


def _parse_trust(payload: object, source_path: str) -> PackTrustSettings | None:
    if payload is None:
        return None
    data = _require_mapping(payload, "trust")
    _reject_unknown_keys(data, _ALLOWED_TRUST_KEYS, source_path)
    propose = _optional_str(data.get("who_can_propose"), "who_can_propose", source_path)
    approve = _optional_str(data.get("who_can_approve"), "who_can_approve", source_path)
    reject = _optional_str(data.get("who_can_reject"), "who_can_reject", source_path)
    approval_count = _optional_int(data.get("approval_count_required"), "approval_count_required", source_path)
    owner_override = _optional_bool(data.get("owner_override"), "owner_override", source_path)
    for field_name, value in (
        ("who_can_propose", propose),
        ("who_can_approve", approve),
        ("who_can_reject", reject),
    ):
        if value is not None and value not in TRUST_LEVELS:
            raise Namel3ssError(
                "Trust level must be one of viewer contributor approver owner."
            )
    if approval_count is not None and approval_count < 1:
        raise Namel3ssError("approval_count_required must be one or more.")
    return PackTrustSettings(
        who_can_propose=propose,
        who_can_approve=approve,
        who_can_reject=reject,
        approval_count_required=approval_count,
        owner_override=owner_override,
    )


def _parse_agreement(payload: object, source_path: str) -> PackAgreementSettings | None:
    if payload is None:
        return None
    data = _require_mapping(payload, "agreement")
    _reject_unknown_keys(data, _ALLOWED_AGREEMENT_KEYS, source_path)
    approval_count = _optional_int(data.get("approval_count_required"), "approval_count_required", source_path)
    owner_override = _optional_bool(data.get("owner_override"), "owner_override", source_path)
    if approval_count is not None and approval_count < 1:
        raise Namel3ssError("approval_count_required must be one or more.")
    return PackAgreementSettings(
        approval_count_required=approval_count,
        owner_override=owner_override,
    )


def _parse_budgets(payload: object, source_path: str) -> list[BudgetConfig] | None:
    if payload is None:
        return None
    if not isinstance(payload, list):
        raise Namel3ssError("Memory pack budgets must be a list of entries.")
    budgets: list[BudgetConfig] = []
    base = BudgetConfig()
    for entry in payload:
        if not isinstance(entry, dict):
            raise Namel3ssError("Memory pack budget entry must be a mapping.")
        _reject_unknown_keys(entry, _ALLOWED_BUDGET_KEYS, source_path)
        cache_enabled = _optional_bool(entry.get("cache_enabled"), "cache_enabled", source_path)
        if cache_enabled is None:
            cache_enabled = base.cache_enabled
        compaction_enabled = _optional_bool(entry.get("compaction_enabled"), "compaction_enabled", source_path)
        if compaction_enabled is None:
            compaction_enabled = base.compaction_enabled
        cache_max_entries = entry.get("cache_max_entries")
        cache_max_entries = int(cache_max_entries) if cache_max_entries is not None else base.cache_max_entries
        budgets.append(
            BudgetConfig(
                space=str(entry.get("space") or base.space or BUDGET_ANY),
                lane=str(entry.get("lane") or base.lane or BUDGET_ANY),
                phase=str(entry.get("phase") or base.phase or BUDGET_ANY),
                owner=str(entry.get("owner") or base.owner or BUDGET_ANY),
                max_items_short_term=_optional_int(entry.get("max_items_short_term"), "max_items_short_term", source_path),
                max_items_semantic=_optional_int(entry.get("max_items_semantic"), "max_items_semantic", source_path),
                max_items_profile=_optional_int(entry.get("max_items_profile"), "max_items_profile", source_path),
                max_items_team=_optional_int(entry.get("max_items_team"), "max_items_team", source_path),
                max_items_agent=_optional_int(entry.get("max_items_agent"), "max_items_agent", source_path),
                max_links_per_item=_optional_int(entry.get("max_links_per_item"), "max_links_per_item", source_path),
                max_phases_per_lane=_optional_int(entry.get("max_phases_per_lane"), "max_phases_per_lane", source_path),
                cache_enabled=cache_enabled,
                cache_max_entries=cache_max_entries,
                compaction_enabled=compaction_enabled,
            )
        )
    return budgets


def _parse_lanes(payload: object, source_path: str) -> PackLaneDefaults | None:
    if payload is None:
        return None
    data = _require_mapping(payload, "lanes")
    _reject_unknown_keys(data, _ALLOWED_LANE_KEYS, source_path)
    read_order = _optional_str_list(data.get("read_order"), "read_order", source_path)
    write_lanes = _optional_str_list(data.get("write_lanes"), "write_lanes", source_path)
    team_event_types = _optional_str_list(data.get("team_event_types"), "team_event_types", source_path)
    for lane_value in (read_order or []) + (write_lanes or []):
        if lane_value not in LANES:
            raise Namel3ssError("Lane must be one of my team system agent.")
    for event_type in team_event_types or []:
        if event_type not in EVENT_TYPES:
            raise Namel3ssError("Team event types must be valid memory event names.")
    return PackLaneDefaults(
        read_order=read_order,
        write_lanes=write_lanes,
        team_enabled=_optional_bool(data.get("team_enabled"), "team_enabled", source_path),
        system_enabled=_optional_bool(data.get("system_enabled"), "system_enabled", source_path),
        agent_enabled=_optional_bool(data.get("agent_enabled"), "agent_enabled", source_path),
        team_event_types=team_event_types,
        team_can_change=_optional_bool(data.get("team_can_change"), "team_can_change", source_path),
    )


def _parse_phase(payload: object, source_path: str) -> PackPhaseDefaults | None:
    if payload is None:
        return None
    data = _require_mapping(payload, "phase")
    _reject_unknown_keys(data, _ALLOWED_PHASE_KEYS, source_path)
    return PackPhaseDefaults(
        enabled=_optional_bool(data.get("enabled"), "enabled", source_path),
        mode=_optional_str(data.get("mode"), "mode", source_path),
        allow_cross_phase_recall=_optional_bool(
            data.get("allow_cross_phase_recall"),
            "allow_cross_phase_recall",
            source_path,
        ),
        max_phases=_optional_int(data.get("max_phases"), "max_phases", source_path),
        diff_enabled=_optional_bool(data.get("diff_enabled"), "diff_enabled", source_path),
    )


def _required_str(value: object, field: str, source_path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(f"Memory pack {field} must be a non empty string.")
    return value.strip()


def _optional_str(value: object, field: str, source_path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise Namel3ssError(f"Memory pack {field} must be a string.")
    text = value.strip()
    return text if text else None


def _optional_int(value: object, field: str, source_path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Namel3ssError(f"Memory pack {field} must be a number.")
    try:
        return int(value)
    except Exception as err:
        raise Namel3ssError(f"Memory pack {field} must be a number.") from err


def _optional_bool(value: object, field: str, source_path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise Namel3ssError(f"Memory pack {field} must be true or false.")
    return bool(value)


def _optional_str_list(value: object, field: str, source_path: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise Namel3ssError(f"Memory pack {field} must be a list of strings.")
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise Namel3ssError(f"Memory pack {field} must be a list of strings.")
        text = entry.strip()
        if text:
            items.append(text)
    return items


def _require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError("Memory pack data must be a mapping.")
    return value


def _reject_unknown_keys(payload: dict, allowed: set[str], source_path: str) -> None:
    unknown = [key for key in payload.keys() if key not in allowed]
    if unknown:
        raise Namel3ssError("Memory pack has unknown fields.")


__all__ = ["validate_overrides_payload", "validate_pack_payload"]
