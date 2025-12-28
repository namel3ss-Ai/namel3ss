from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.helpers import build_deleted_events, build_forget_events
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_SYSTEM, agent_lane_key, lanes_for_space
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION, SpaceContext
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract


def _retention_spaces(read_order: list[str], promoted_items: list[MemoryItem]) -> list[str]:
    ordered = list(read_order or [SPACE_SESSION])
    extras: list[str] = []
    for item in promoted_items:
        space = item.meta.get("space")
        if isinstance(space, str) and space not in ordered and space not in extras:
            extras.append(space)
    if extras:
        ordered.extend(sorted(extras))
    return ordered


def _apply_retention(
    *,
    ai_profile: str,
    session: str,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    space_ctx: SpaceContext,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    promoted_items: list[MemoryItem],
    now_tick: int,
    phase_policy_snapshot: dict,
    agent_id: str | None,
) -> list[dict]:
    events: list[dict] = []
    spaces_for_retention = _retention_spaces(contract.spaces.read_order, promoted_items)
    for space in spaces_for_retention:
        for lane in lanes_for_space(space, read_order=contract.lanes.read_order):
            if lane == LANE_AGENT and not agent_id:
                continue
            if lane == LANE_AGENT:
                store_key = agent_lane_key(space_ctx, space=space, agent_id=agent_id or "")
            else:
                store_key = space_ctx.store_key_for(space, lane=lane)
            owner = space_ctx.owner_for(space)
            phase = phase_registry.current(store_key)
            if lane == LANE_SYSTEM:
                continue
            if policy.semantic_enabled:
                forgotten = semantic.apply_retention(store_key, contract, now_tick)
                events.extend(build_forget_events(ai_profile, session, forgotten, contract))
                if forgotten and phase:
                    removed = [item for item, _ in forgotten]
                    events.extend(
                        build_deleted_events(
                            ai_profile,
                            session,
                            space=space,
                            owner=owner,
                            phase=phase,
                            removed=removed,
                            reason="expired",
                            policy_snapshot=phase_policy_snapshot,
                            replaced_by=None,
                        )
                    )
                    for item in removed:
                        phase_ledger.record_delete(store_key, phase=phase, memory_id=item.id)
            if policy.profile_enabled:
                forgotten = profile.apply_retention(store_key, contract, now_tick)
                events.extend(build_forget_events(ai_profile, session, forgotten, contract))
                if forgotten and phase:
                    removed = [item for item, _ in forgotten]
                    events.extend(
                        build_deleted_events(
                            ai_profile,
                            session,
                            space=space,
                            owner=owner,
                            phase=phase,
                            removed=removed,
                            reason="expired",
                            policy_snapshot=phase_policy_snapshot,
                            replaced_by=None,
                        )
                    )
                    for item in removed:
                        phase_ledger.record_delete(store_key, phase=phase, memory_id=item.id)
    return events


__all__ = ["_apply_retention"]
