from __future__ import annotations

from namel3ss.runtime.memory.helpers import build_border_event
from namel3ss.runtime.memory_policy.evaluation import evaluate_phase_start
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.traces.builders import build_memory_phase_started


def _phase_ids_between(ledger: PhaseLedger, store_key: str, from_phase_id: str, to_phase_id: str) -> list[str]:
    order = ledger.phase_ids(store_key)
    if not order:
        return [from_phase_id] if from_phase_id == to_phase_id else [from_phase_id, to_phase_id]
    if from_phase_id not in order or to_phase_id not in order:
        return [from_phase_id] if from_phase_id == to_phase_id else [from_phase_id, to_phase_id]
    start = order.index(from_phase_id)
    end = order.index(to_phase_id)
    if start <= end:
        return order[start : end + 1]
    subset = order[end : start + 1]
    subset.reverse()
    return subset


def _ensure_phase_for_store(
    *,
    ai_profile: str,
    session: str,
    space: str,
    owner: str,
    store_key: str,
    contract: MemoryPolicyContract,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    request: PhaseRequest | None,
    default_reason: str,
    lane: str,
) -> tuple[object, list[dict]]:
    events: list[dict] = []
    current = phase_registry.current(store_key)
    should_attempt = request is not None or current is None
    if not should_attempt and current is not None:
        return current, events
    decision = evaluate_phase_start(contract.phase)
    events.append(
        build_border_event(
            ai_profile=ai_profile,
            session=session,
            action="phase_start",
            from_space=space,
            to_space=None,
            allowed=decision.allowed,
            reason=decision.reason,
            subject_id=None,
            policy_snapshot={"phase": contract.phase.as_dict()},
            from_lane=lane,
            to_lane=None,
        )
    )
    if not decision.allowed:
        if current is None:
            current = phase_registry.start_phase(store_key, reason=default_reason)
            phase_ledger.start_phase(store_key, phase=current, previous=None)
            phase_ledger.cleanup(store_key, contract.phase.max_phases)
            events.append(
                build_memory_phase_started(
                    ai_profile=ai_profile,
                    session=session,
                    space=space,
                    owner=owner,
                    phase_id=current.phase_id,
                    phase_name=current.name,
                    reason=current.reason,
                    policy_snapshot={"phase": contract.phase.as_dict()},
                    lane=lane,
                )
            )
        return current, events
    previous = phase_registry.current(store_key)
    phase, started = phase_registry.ensure_phase(store_key, request=request, default_reason=default_reason)
    if started:
        phase_ledger.start_phase(store_key, phase=phase, previous=previous)
        phase_ledger.cleanup(store_key, contract.phase.max_phases)
        events.append(
            build_memory_phase_started(
                ai_profile=ai_profile,
                session=session,
                space=space,
                owner=owner,
                phase_id=phase.phase_id,
                phase_name=phase.name,
                reason=phase.reason,
                policy_snapshot={"phase": contract.phase.as_dict()},
                lane=lane,
            )
        )
    return phase, events
