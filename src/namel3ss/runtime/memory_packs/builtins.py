from __future__ import annotations

from namel3ss.runtime.memory.events import EVENT_DECISION, EVENT_EXECUTION, EVENT_RULE
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_MY, LANE_TEAM
from namel3ss.runtime.memory_packs.format import (
    MemoryPack,
    PackAgreementSettings,
    PackLaneDefaults,
    PackTrustSettings,
)


def builtin_memory_packs() -> list[MemoryPack]:
    packs = [
        _agent_minimal_pack(),
        _agent_collab_pack(),
        _agent_strict_privacy_pack(),
    ]
    return sorted(packs, key=lambda pack: pack.pack_id)


def _agent_minimal_pack() -> MemoryPack:
    lanes = PackLaneDefaults(
        read_order=[LANE_MY, LANE_AGENT],
        write_lanes=[LANE_MY, LANE_AGENT],
        team_enabled=False,
        system_enabled=False,
        agent_enabled=True,
        team_event_types=[],
        team_can_change=False,
    )
    return MemoryPack(
        pack_id="agent-minimal",
        pack_name="Agent minimal",
        pack_version="1.0.0",
        rules=None,
        trust=None,
        agreement=None,
        budgets=None,
        lanes=lanes,
        phase=None,
        source_path="builtin",
    )


def _agent_collab_pack() -> MemoryPack:
    lanes = PackLaneDefaults(
        read_order=[LANE_MY, LANE_AGENT, LANE_TEAM],
        write_lanes=[LANE_MY, LANE_AGENT],
        team_enabled=True,
        system_enabled=False,
        agent_enabled=True,
        team_event_types=[EVENT_DECISION, EVENT_RULE, EVENT_EXECUTION],
        team_can_change=True,
    )
    agreement = PackAgreementSettings(
        approval_count_required=2,
        owner_override=True,
    )
    trust = PackTrustSettings(
        who_can_propose="contributor",
        who_can_approve="approver",
        who_can_reject="approver",
        approval_count_required=2,
        owner_override=True,
    )
    return MemoryPack(
        pack_id="agent-collab",
        pack_name="Agent collab",
        pack_version="1.0.0",
        rules=None,
        trust=trust,
        agreement=agreement,
        budgets=None,
        lanes=lanes,
        phase=None,
        source_path="builtin",
    )


def _agent_strict_privacy_pack() -> MemoryPack:
    lanes = PackLaneDefaults(
        read_order=[LANE_MY, LANE_AGENT],
        write_lanes=[LANE_MY, LANE_AGENT],
        team_enabled=False,
        system_enabled=False,
        agent_enabled=True,
        team_event_types=[],
        team_can_change=False,
    )
    trust = PackTrustSettings(
        who_can_propose="owner",
        who_can_approve="owner",
        who_can_reject="owner",
        approval_count_required=1,
        owner_override=False,
    )
    agreement = PackAgreementSettings(
        approval_count_required=1,
        owner_override=False,
    )
    return MemoryPack(
        pack_id="agent-strict-privacy",
        pack_name="Agent strict privacy",
        pack_version="1.0.0",
        rules=None,
        trust=trust,
        agreement=agreement,
        budgets=None,
        lanes=lanes,
        phase=None,
        source_path="builtin",
    )


__all__ = ["builtin_memory_packs"]
