from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.memory_budget.model import BudgetConfig


MEMORY_PACK_VERSION = "memory_pack_v1"


@dataclass(frozen=True)
class PackTrustSettings:
    who_can_propose: str | None = None
    who_can_approve: str | None = None
    who_can_reject: str | None = None
    approval_count_required: int | None = None
    owner_override: bool | None = None


@dataclass(frozen=True)
class PackAgreementSettings:
    approval_count_required: int | None = None
    owner_override: bool | None = None


@dataclass(frozen=True)
class PackLaneDefaults:
    read_order: list[str] | None = None
    write_lanes: list[str] | None = None
    team_enabled: bool | None = None
    system_enabled: bool | None = None
    agent_enabled: bool | None = None
    team_event_types: list[str] | None = None
    team_can_change: bool | None = None


@dataclass(frozen=True)
class PackPhaseDefaults:
    enabled: bool | None = None
    mode: str | None = None
    allow_cross_phase_recall: bool | None = None
    max_phases: int | None = None
    diff_enabled: bool | None = None


@dataclass(frozen=True)
class MemoryPack:
    pack_id: str
    pack_name: str
    pack_version: str
    rules: list[str] | None
    trust: PackTrustSettings | None
    agreement: PackAgreementSettings | None
    budgets: list[BudgetConfig] | None
    lanes: PackLaneDefaults | None
    phase: PackPhaseDefaults | None
    source_path: str | None = None


@dataclass(frozen=True)
class MemoryOverrides:
    rules: list[str] | None
    trust: PackTrustSettings | None
    agreement: PackAgreementSettings | None
    budgets: list[BudgetConfig] | None
    lanes: PackLaneDefaults | None
    phase: PackPhaseDefaults | None
    source_path: str | None = None


__all__ = [
    "MEMORY_PACK_VERSION",
    "MemoryOverrides",
    "MemoryPack",
    "PackAgreementSettings",
    "PackLaneDefaults",
    "PackPhaseDefaults",
    "PackTrustSettings",
]
