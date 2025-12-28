from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.helpers import build_border_event
from namel3ss.runtime.memory_policy.evaluation import evaluate_border_write, evaluate_lane_write
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract


def _build_write_allowed(
    *,
    ai_profile: str,
    session: str,
    contract: MemoryPolicyContract,
    policy_snapshot: dict,
    events: list[dict],
    budget_enforcer,
    store_key: str,
    space: str,
    owner: str,
    phase,
) -> callable:
    def _write_allowed(item: MemoryItem, *, lane: str) -> bool:
        decision = evaluate_border_write(contract, space=space)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="write",
                from_space=space,
                to_space=space,
                allowed=decision.allowed,
                reason=decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
                from_lane=lane,
                to_lane=lane,
            )
        )
        lane_decision = evaluate_lane_write(contract, lane=lane, space=space)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="lane_write",
                from_space=space,
                to_space=space,
                allowed=lane_decision.allowed,
                reason=lane_decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
                from_lane=lane,
                to_lane=lane,
            )
        )
        if not (decision.allowed and lane_decision.allowed):
            return False
        return budget_enforcer.allow_write(
            store_key=store_key,
            space=space,
            owner=owner,
            lane=lane,
            phase=phase,
            kind=item.kind.value,
            incoming=1,
        )

    return _write_allowed


__all__ = ["_build_write_allowed"]
