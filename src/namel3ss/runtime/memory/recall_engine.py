from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryClock, MemoryItem, normalize_memory_item, validate_memory_item
from namel3ss.runtime.memory_budget import BudgetConfig, select_budget
from namel3ss.runtime.memory_cache import build_cache_event, build_cache_key, fingerprint_policy, fingerprint_query, use_cache
from namel3ss.runtime.memory.helpers import (
    apply_recall_policy_tags,
    build_border_event,
    build_deleted_events,
    build_forget_events,
)
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION, SpaceContext, ensure_space_meta, validate_space_rules
from namel3ss.runtime.memory_lanes.model import (
    LANE_AGENT,
    LANE_MY,
    LANE_SYSTEM,
    agent_lane_key,
    ensure_lane_meta,
    lanes_for_space,
    validate_lane_rules,
)
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_policy.evaluation import (
    evaluate_border_read,
    evaluate_lane_read,
    evaluate_phase_start,
)
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.traces.builders import build_memory_phase_started


def recall_context_with_events(
    *,
    ai_profile: str,
    session: str,
    user_input: str,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    clock: MemoryClock,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    budget_configs: list[BudgetConfig] | None = None,
    cache_store=None,
    cache_version_for=None,
    cache_bump=None,
    agent_id: str | None = None,
) -> tuple[dict, list[dict], dict]:
    events: list[dict] = []
    context = {"short_term": [], "semantic": [], "profile": []}
    now_tick = clock.current()
    spaces_consulted = list(contract.spaces.read_order or [SPACE_SESSION])
    recall_counts: dict[str, int] = {}
    phase_counts: dict[str, dict[str, int]] = {}
    budget_configs = budget_configs or []
    policy_snapshot = _policy_snapshot_for_cache(policy, contract)
    query_fingerprint = fingerprint_query(user_input)
    policy_fingerprint = fingerprint_policy(policy_snapshot)
    if phase_request is not None:
        _, phase_events = _ensure_phase_for_recall(
            ai_profile=ai_profile,
            session=session,
            space=SPACE_SESSION,
            owner=space_ctx.owner_for(SPACE_SESSION),
            store_key=space_ctx.store_key_for(SPACE_SESSION, lane=LANE_MY),
            contract=contract,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            request=phase_request,
        )
        events.extend(phase_events)
    for space in spaces_consulted:
        decision = evaluate_border_read(contract, space=space)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="read",
                from_space=space,
                to_space=None,
                allowed=decision.allowed,
                reason=decision.reason,
                subject_id=None,
                policy_snapshot=contract.as_dict(),
            )
        )
        if not decision.allowed:
            recall_counts[space] = 0
            continue
        count = 0
        space_items: list[MemoryItem] = []
        for lane in lanes_for_space(space, read_order=contract.lanes.read_order):
            if lane == LANE_AGENT and not agent_id:
                continue
            lane_decision = evaluate_lane_read(contract, lane=lane, space=space)
            events.append(
                build_border_event(
                    ai_profile=ai_profile,
                    session=session,
                    action="lane_read",
                    from_space=space,
                    to_space=None,
                    allowed=lane_decision.allowed,
                    reason=lane_decision.reason,
                    subject_id=None,
                    policy_snapshot=contract.as_dict(),
                    from_lane=lane,
                    to_lane=None,
                )
            )
            if not lane_decision.allowed:
                continue
            if lane == LANE_AGENT:
                store_key = agent_lane_key(space_ctx, space=space, agent_id=agent_id or "")
            else:
                store_key = space_ctx.store_key_for(space, lane=lane)
            owner = space_ctx.owner_for(space)
            current_phase = phase_registry.current(store_key)
            phase_ids = _phase_ids_for_recall(phase_registry, store_key, policy)
            if policy.semantic_enabled and lane != LANE_SYSTEM:
                forgotten = semantic.apply_retention(store_key, contract, now_tick)
                events.extend(build_forget_events(ai_profile, session, forgotten, contract))
                if forgotten and current_phase:
                    removed = [item for item, _ in forgotten]
                    events.extend(
                        build_deleted_events(
                            ai_profile,
                            session,
                            space=space,
                            owner=owner,
                            phase=current_phase,
                            removed=removed,
                            reason="expired",
                            policy_snapshot={"phase": contract.phase.as_dict()},
                            replaced_by=None,
                        )
                    )
                    for item in removed:
                        phase_ledger.record_delete(store_key, phase=current_phase, memory_id=item.id)
                if forgotten and cache_bump:
                    cache_bump(store_key, "semantic")
            if policy.profile_enabled and lane != LANE_SYSTEM:
                forgotten = profile.apply_retention(store_key, contract, now_tick)
                events.extend(build_forget_events(ai_profile, session, forgotten, contract))
                if forgotten and current_phase:
                    removed = [item for item, _ in forgotten]
                    events.extend(
                        build_deleted_events(
                            ai_profile,
                            session,
                            space=space,
                            owner=owner,
                            phase=current_phase,
                            removed=removed,
                            reason="expired",
                            policy_snapshot={"phase": contract.phase.as_dict()},
                            replaced_by=None,
                        )
                    )
                    for item in removed:
                        phase_ledger.record_delete(store_key, phase=current_phase, memory_id=item.id)
                if forgotten and cache_bump:
                    cache_bump(store_key, "profile")
            phase_id = current_phase.phase_id if current_phase else "phase-unknown"
            config = select_budget(budget_configs, space=space, lane=lane, phase=phase_id, owner=owner)
            cache_enabled = bool(config.cache_enabled) if config else False
            if cache_store and config and config.cache_max_entries is not None:
                cache_store.set_max_entries(config.cache_max_entries)
            kinds_for_cache: list[str] = []
            if policy.short_term_max_turns > 0:
                kinds_for_cache.append("short_term")
            if policy.semantic_enabled:
                kinds_for_cache.append("semantic")
            if policy.profile_enabled:
                kinds_for_cache.append("profile")
            cache_version = cache_version_for(store_key, kinds_for_cache) if cache_version_for else 0
            cache_key = build_cache_key(
                space=space,
                lane=lane,
                phase_id=phase_id,
                ai_profile=ai_profile,
                store_key=store_key,
                query_fingerprint=query_fingerprint,
                policy_fingerprint=policy_fingerprint,
            )

            def _compute_lane():
                lane_result = {"short_term": [], "semantic": [], "profile": []}
                if policy.short_term_max_turns > 0:
                    items = short_term.recall(store_key, policy.short_term_max_turns, phase_ids=phase_ids)
                    lane_result["short_term"] = [
                        _with_space_recall(item, space=space, owner=owner, lane=lane, agent_id=agent_id)
                        for item in items
                    ]
                if policy.semantic_enabled:
                    items = semantic.recall(store_key, user_input, top_k=policy.semantic_top_k, phase_ids=phase_ids)
                    lane_result["semantic"] = [
                        _with_space_recall(item, space=space, owner=owner, lane=lane, agent_id=agent_id)
                        for item in items
                    ]
                if policy.profile_enabled:
                    items = profile.recall(store_key, phase_ids=phase_ids)
                    lane_result["profile"] = [
                        _with_space_recall(item, space=space, owner=owner, lane=lane, agent_id=agent_id)
                        for item in items
                    ]
                return lane_result

            lane_result, cache_hit = use_cache(
                cache=cache_store,
                cache_enabled=cache_enabled,
                cache_key=cache_key,
                cache_version=cache_version,
                compute=_compute_lane,
            )
            if cache_hit is not None:
                events.append(
                    build_cache_event(
                        ai_profile=ai_profile,
                        session=session,
                        space=space,
                        lane=lane,
                        phase_id=phase_id,
                        hit=cache_hit,
                    )
                )
            for key, items in lane_result.items():
                if items:
                    context[key].extend(items)
                    count += len(items)
                    space_items.extend(items)
        recall_counts[space] = count
        if space_items:
            phase_counts[space] = _count_by_phase(space_items)
    normalized = {key: [normalize_memory_item(item) for item in items] for key, items in context.items()}
    apply_recall_policy_tags(normalized, contract)
    for items in normalized.values():
        for item in items:
            validate_memory_item(item)
            validate_space_rules(item)
            validate_lane_rules(item)
    current_phase = phase_registry.current(space_ctx.store_key_for(SPACE_SESSION, lane=LANE_MY))
    return normalized, events, {
        "spaces_consulted": spaces_consulted,
        "recall_counts": recall_counts,
        "phase_counts": phase_counts,
        "current_phase": _phase_meta(current_phase),
    }


def _with_space_recall(item: MemoryItem, *, space: str, owner: str, lane: str, agent_id: str | None) -> MemoryItem:
    meta = ensure_space_meta(item.meta, space=space, owner=owner)
    meta = ensure_lane_meta(meta, lane=lane, agent_id=agent_id if lane == LANE_AGENT else None)
    reasons = list(meta.get("recall_reason", []))
    space_tag = f"space:{space}"
    if space_tag not in reasons:
        reasons.append(space_tag)
    lane_tag = f"lane:{lane}"
    if lane_tag not in reasons:
        reasons.append(lane_tag)
    meta["recall_reason"] = reasons
    return replace(item, meta=meta)


def _phase_ids_for_recall(registry: PhaseRegistry, store_key: str, policy: MemoryPolicy) -> list[str]:
    current = registry.current(store_key)
    if current is None:
        return []
    if not policy.allow_cross_phase_recall:
        return [current.phase_id]
    phases = registry.phases(store_key)
    phases.sort(key=lambda entry: entry.phase_index, reverse=True)
    return [phase.phase_id for phase in phases]


def _count_by_phase(items: list[MemoryItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        meta = None
        if hasattr(item, "meta"):
            meta = item.meta
        elif isinstance(item, dict):
            meta = item.get("meta")
        phase_id = meta.get("phase_id") if isinstance(meta, dict) else None
        if not phase_id:
            continue
        counts[phase_id] = counts.get(phase_id, 0) + 1
    return counts


def _ensure_phase_for_recall(
    *,
    ai_profile: str,
    session: str,
    space: str,
    owner: str,
    store_key: str,
    contract: MemoryPolicyContract,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    request: PhaseRequest,
) -> tuple[object, list[dict]]:
    events: list[dict] = []
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
            from_lane=LANE_MY,
            to_lane=None,
        )
    )
    if not decision.allowed:
        current = phase_registry.current(store_key)
        return current, events
    previous = phase_registry.current(store_key)
    phase, started = phase_registry.ensure_phase(store_key, request=request, default_reason="manual")
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
                lane=LANE_MY,
            )
        )
    return phase, events


def _phase_meta(phase) -> dict | None:
    if phase is None:
        return None
    payload = {
        "phase_id": phase.phase_id,
        "phase_index": phase.phase_index,
        "phase_started_at": phase.started_at,
        "phase_reason": phase.reason,
    }
    if phase.name:
        payload["phase_name"] = phase.name
    return payload


def _policy_snapshot_for_cache(policy: MemoryPolicy, contract: MemoryPolicyContract) -> dict:
    snapshot = policy.as_trace_dict()
    snapshot.update(contract.as_dict())
    return snapshot


__all__ = ["recall_context_with_events"]
