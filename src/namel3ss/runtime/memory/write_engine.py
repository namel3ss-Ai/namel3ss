from __future__ import annotations

from namel3ss.runtime.memory.contract import (
    MemoryClock,
    MemoryItem,
    MemoryItemFactory,
    MemoryKind,
    normalize_memory_item,
    validate_memory_item,
)
from namel3ss.runtime.memory.events import EVENT_CONTEXT, EVENT_CORRECTION, EVENT_FACT, classify_event_type
from namel3ss.runtime.memory.facts import extract_fact
from namel3ss.runtime.memory.helpers import (
    authority_for_source,
    build_border_event,
    build_conflict_event,
    build_deleted_event,
    build_deleted_events,
    build_denied_event,
    build_forget_event,
    build_forget_events,
    build_meta,
    should_attempt_profile,
    should_attempt_semantic,
    with_policy_tags,
)
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.promotion import infer_promotion_request, promotion_request_for_item
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION, SpaceContext, validate_space_rules
from namel3ss.runtime.memory_timeline.diff import PhaseDiffRequest, diff_phases
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta
from namel3ss.runtime.memory_policy.evaluation import (
    evaluate_border_read,
    evaluate_border_write,
    evaluate_phase_diff,
    evaluate_phase_start,
    evaluate_promotion,
    evaluate_write,
)
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.traces.builders import (
    build_memory_phase_diff,
    build_memory_phase_started,
    build_memory_promoted,
    build_memory_promotion_denied,
)


def record_interaction_with_events(
    *,
    ai_profile: str,
    session: str,
    user_input: str,
    ai_output: str,
    tool_events: list[dict],
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    clock: MemoryClock,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    phase_diff_request: PhaseDiffRequest | None,
) -> tuple[list[dict], list[dict]]:
    events: list[dict] = []
    written: list[MemoryItem] = []
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    session_owner = space_ctx.owner_for(SPACE_SESSION)
    session_key = space_ctx.store_key_for(SPACE_SESSION)
    session_phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai_profile,
        session=session,
        space=SPACE_SESSION,
        owner=session_owner,
        store_key=session_key,
        contract=contract,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        request=phase_request,
        default_reason="auto",
    )
    events.extend(phase_events)

    promotion_request = infer_promotion_request(user_input)
    promotion_target = promotion_request.target_space if promotion_request else None
    promotion_reason = promotion_request.reason if promotion_request else None

    def _write_allowed(item: MemoryItem) -> bool:
        decision = evaluate_border_write(contract, space=SPACE_SESSION)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="write",
                from_space=SPACE_SESSION,
                to_space=SPACE_SESSION,
                allowed=decision.allowed,
                reason=decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
            )
        )
        return decision.allowed

    user_event_type = classify_event_type(user_input)
    user_importance, user_reasons = importance_for_event(user_event_type, user_input, "user")
    user_authority, user_authority_reason = authority_for_source("user")
    user_meta = build_meta(
        user_event_type,
        user_reasons,
        user_input,
        authority=user_authority,
        authority_reason=user_authority_reason,
        space=SPACE_SESSION,
        owner=session_owner,
        phase=session_phase,
        promotion_target=promotion_target,
        promotion_reason=promotion_reason,
    )
    user_item = factory.create(
        session=session_key,
        kind=MemoryKind.SHORT_TERM,
        text=user_input,
        source="user",
        importance=user_importance,
        meta=user_meta,
    )
    decision = evaluate_write(contract, user_item, event_type=user_event_type)
    stored_user: MemoryItem | None = None
    if _write_allowed(user_item):
        if decision.allowed:
            user_item = with_policy_tags(user_item, decision.tags)
            short_term.store_item(session_key, user_item)
            phase_ledger.record_add(session_key, phase=session_phase, item=user_item)
            written.append(user_item)
            stored_user = user_item
        else:
            events.append(build_denied_event(ai_profile, session, user_item, decision, policy_snapshot))

    ai_event_type = EVENT_CONTEXT
    ai_importance, ai_reasons = importance_for_event(ai_event_type, ai_output, "ai")
    ai_authority, ai_authority_reason = authority_for_source("ai")
    ai_meta = build_meta(
        ai_event_type,
        ai_reasons,
        ai_output,
        authority=ai_authority,
        authority_reason=ai_authority_reason,
        space=SPACE_SESSION,
        owner=session_owner,
        phase=session_phase,
    )
    ai_item = factory.create(
        session=session_key,
        kind=MemoryKind.SHORT_TERM,
        text=ai_output,
        source="ai",
        importance=ai_importance,
        meta=ai_meta,
    )
    decision = evaluate_write(contract, ai_item, event_type=ai_event_type)
    if _write_allowed(ai_item):
        if decision.allowed:
            ai_item = with_policy_tags(ai_item, decision.tags)
            short_term.store_item(session_key, ai_item)
            phase_ledger.record_add(session_key, phase=session_phase, item=ai_item)
            written.append(ai_item)
        else:
            events.append(build_denied_event(ai_profile, session, ai_item, decision, policy_snapshot))

    summary_item, evicted, replaced_summary = short_term.summarize_if_needed(
        session_key,
        policy.short_term_max_turns,
        phase_id=session_phase.phase_id,
        space=SPACE_SESSION,
        owner=session_owner,
    )
    if summary_item:
        phase_ledger.record_add(session_key, phase=session_phase, item=summary_item)
        written.append(summary_item)
    if replaced_summary:
        events.append(
            build_deleted_event(
                ai_profile,
                session,
                space=SPACE_SESSION,
                owner=session_owner,
                phase=session_phase,
                item=replaced_summary,
                reason="superseded",
                policy_snapshot=phase_policy_snapshot,
                replaced_by=summary_item.id if summary_item else None,
            )
        )
        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=replaced_summary.id)
    if evicted:
        events.extend(build_forget_events(ai_profile, session, [(item, "decay") for item in evicted], contract))
        events.extend(
            build_deleted_events(
                ai_profile,
                session,
                space=SPACE_SESSION,
                owner=session_owner,
                phase=session_phase,
                removed=evicted,
                reason="expired",
                policy_snapshot=phase_policy_snapshot,
                replaced_by=None,
            )
        )
        for item in evicted:
            phase_ledger.record_delete(session_key, phase=session_phase, memory_id=item.id)

    fact = extract_fact(user_input)
    is_correction = user_event_type == EVENT_CORRECTION
    if policy.semantic_enabled and should_attempt_semantic(user_event_type, user_input, policy.write_policy):
        semantic_authority, semantic_authority_reason = authority_for_source("user")
        semantic_meta = build_meta(
            user_event_type,
            user_reasons,
            user_input,
            authority=semantic_authority,
            authority_reason=semantic_authority_reason,
            space=SPACE_SESSION,
            owner=session_owner,
            phase=session_phase,
            promotion_target=promotion_target,
            promotion_reason=promotion_reason,
        )
        semantic_item = factory.create(
            session=session_key,
            kind=MemoryKind.SEMANTIC,
            text=user_input,
            source="user",
            importance=user_importance,
            meta=semantic_meta,
        )
        decision = evaluate_write(contract, semantic_item, event_type=user_event_type)
        if _write_allowed(semantic_item):
            if decision.allowed:
                semantic_item = with_policy_tags(semantic_item, decision.tags)
                stored_item, conflict, deleted = semantic.store_item(
                    session_key,
                    semantic_item,
                    dedupe_enabled=policy.dedupe_enabled,
                    authority_order=contract.authority_order,
                )
                if stored_item and stored_item.id == semantic_item.id:
                    written.append(stored_item)
                    phase_ledger.record_add(session_key, phase=session_phase, item=stored_item)
                if conflict:
                    events.append(build_conflict_event(ai_profile, session, conflict))
                    if deleted:
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="superseded",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
            else:
                events.append(build_denied_event(ai_profile, session, semantic_item, decision, policy_snapshot))

    if policy.profile_enabled and fact and should_attempt_profile(user_event_type):
        profile_event_type = EVENT_CORRECTION if is_correction else EVENT_FACT
        profile_authority, profile_authority_reason = authority_for_source("user")
        profile_meta = build_meta(
            profile_event_type,
            user_reasons,
            fact.value,
            authority=profile_authority,
            authority_reason=profile_authority_reason,
            dedup_key=f"fact:{fact.key}",
            space=SPACE_SESSION,
            owner=session_owner,
            phase=session_phase,
            promotion_target=promotion_target,
            promotion_reason=promotion_reason,
        )
        profile_meta["key"] = fact.key
        if stored_user:
            profile_meta["source_turn_ids"] = [stored_user.id]
        profile_item = factory.create(
            session=session_key,
            kind=MemoryKind.PROFILE,
            text=fact.value,
            source="user",
            importance=user_importance,
            meta=profile_meta,
        )
        decision = evaluate_write(
            contract,
            profile_item,
            event_type=profile_event_type,
            privacy_text=user_input,
        )
        if _write_allowed(profile_item):
            if decision.allowed:
                profile_item = with_policy_tags(profile_item, decision.tags)
                stored_item, conflict, deleted = profile.store_item(
                    session_key,
                    profile_item,
                    dedupe_enabled=policy.dedupe_enabled,
                    authority_order=contract.authority_order,
                )
                if stored_item and stored_item.id == profile_item.id:
                    written.append(stored_item)
                    phase_ledger.record_add(session_key, phase=session_phase, item=stored_item)
                if conflict:
                    events.append(build_conflict_event(ai_profile, session, conflict))
                    if deleted:
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="superseded",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
            else:
                events.append(build_denied_event(ai_profile, session, profile_item, decision, policy_snapshot))

    if policy.semantic_enabled and tool_events:
        event_type = classify_event_type("", has_tool_events=True)
        text = f"tool_events:{tool_events}"
        importance, reasons = importance_for_event(event_type, text, "tool")
        tool_authority, tool_authority_reason = authority_for_source("tool")
        meta = build_meta(
            event_type,
            reasons,
            text,
            authority=tool_authority,
            authority_reason=tool_authority_reason,
            space=SPACE_SESSION,
            owner=session_owner,
            phase=session_phase,
        )
        tool_item = factory.create(
            session=session_key,
            kind=MemoryKind.SEMANTIC,
            text=text,
            source="tool",
            importance=importance,
            meta=meta,
        )
        decision = evaluate_write(contract, tool_item, event_type=event_type)
        if _write_allowed(tool_item):
            if decision.allowed:
                tool_item = with_policy_tags(tool_item, decision.tags)
                stored_item, conflict, deleted = semantic.store_item(
                    session_key,
                    tool_item,
                    dedupe_enabled=policy.dedupe_enabled,
                    authority_order=contract.authority_order,
                )
                if stored_item and stored_item.id == tool_item.id:
                    written.append(stored_item)
                    phase_ledger.record_add(session_key, phase=session_phase, item=stored_item)
                if conflict:
                    events.append(build_conflict_event(ai_profile, session, conflict))
                    if deleted:
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="superseded",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
            else:
                events.append(build_denied_event(ai_profile, session, tool_item, decision, policy_snapshot))

    promoted_items, promotion_events = _promote_items(
        ai_profile=ai_profile,
        session=session,
        items=written,
        space_ctx=space_ctx,
        policy=policy,
        contract=contract,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        session_phase=session_phase,
    )
    if promoted_items:
        written.extend(promoted_items)
    if promotion_events:
        events.extend(promotion_events)

    now_tick = clock.current()
    spaces_for_retention = _retention_spaces(contract.spaces.read_order, promoted_items)
    for space in spaces_for_retention:
        store_key = space_ctx.store_key_for(space)
        owner = space_ctx.owner_for(space)
        phase = phase_registry.current(store_key)
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

    if phase_diff_request:
        events.extend(
            _build_phase_diff_events(
                ai_profile=ai_profile,
                session=session,
                diff_request=phase_diff_request,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
            )
        )

    normalized = [normalize_memory_item(item) for item in written]
    for item in normalized:
        validate_memory_item(item)
        validate_space_rules(item)
    return normalized, events


def _promote_items(
    *,
    ai_profile: str,
    session: str,
    items: list[MemoryItem],
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    session_phase,
) -> tuple[list[MemoryItem], list[dict]]:
    promoted: list[MemoryItem] = []
    events: list[dict] = []
    if not items:
        return promoted, events
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    for item in items:
        if item.kind == MemoryKind.SHORT_TERM:
            continue
        if item.meta.get("promoted_from"):
            continue
        request = promotion_request_for_item(item)
        if not request:
            continue
        from_space = item.meta.get("space", SPACE_SESSION)
        to_space = request.target_space
        if from_space == to_space:
            continue
        decision = evaluate_promotion(
            contract,
            item=item,
            from_space=from_space,
            to_space=to_space,
            event_type=item.meta.get("event_type", EVENT_CONTEXT),
        )
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="promote",
                from_space=from_space,
                to_space=to_space,
                allowed=decision.allowed,
                reason=decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
            )
        )
        if not decision.allowed:
            events.append(
                build_memory_promotion_denied(
                    ai_profile=ai_profile,
                    session=session,
                    from_space=from_space,
                    to_space=to_space,
                    memory_id=item.id,
                    allowed=False,
                    reason=decision.reason,
                    policy_snapshot=policy_snapshot,
                )
            )
            continue
        target_owner = space_ctx.owner_for(to_space)
        target_key = space_ctx.store_key_for(to_space)
        target_phase, phase_events = _ensure_phase_for_store(
            ai_profile=ai_profile,
            session=session,
            space=to_space,
            owner=target_owner,
            store_key=target_key,
            contract=contract,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            request=None,
            default_reason="auto",
        )
        events.extend(phase_events)
        promoted_meta = dict(item.meta)
        promoted_meta["space"] = to_space
        promoted_meta["owner"] = target_owner
        promoted_meta["promoted_from"] = item.id
        promoted_meta["promotion_reason"] = request.reason
        promoted_meta = apply_phase_meta(promoted_meta, target_phase)
        promoted_item = factory.create(
            session=target_key,
            kind=item.kind,
            text=item.text,
            source=item.source,
            importance=item.importance,
            meta=promoted_meta,
        )
        conflict = None
        deleted = None
        stored_item = None
        if item.kind == MemoryKind.SEMANTIC:
            stored_item, conflict, deleted = semantic.store_item(
                target_key,
                promoted_item,
                dedupe_enabled=policy.dedupe_enabled,
                authority_order=contract.authority_order,
            )
        elif item.kind == MemoryKind.PROFILE:
            stored_item, conflict, deleted = profile.store_item(
                target_key,
                promoted_item,
                dedupe_enabled=policy.dedupe_enabled,
                authority_order=contract.authority_order,
            )
        stored_is_new = stored_item is not None and stored_item.id == promoted_item.id
        if stored_is_new:
            promoted.append(stored_item)
            phase_ledger.record_add(target_key, phase=target_phase, item=stored_item)
        if conflict:
            events.append(build_conflict_event(ai_profile, session, conflict))
            if deleted:
                events.append(
                    build_deleted_event(
                        ai_profile,
                        session,
                        space=to_space,
                        owner=target_owner,
                        phase=target_phase,
                        item=deleted,
                        reason="superseded",
                        policy_snapshot=phase_policy_snapshot,
                        replaced_by=stored_item.id if stored_item else None,
                    )
                )
                phase_ledger.record_delete(target_key, phase=target_phase, memory_id=deleted.id)
        if stored_is_new:
            events.append(
                build_memory_promoted(
                    ai_profile=ai_profile,
                    session=session,
                    from_space=from_space,
                    to_space=to_space,
                    from_id=item.id,
                    to_id=stored_item.id,
                    authority_used=decision.authority_used,
                    reason=request.reason,
                    policy_snapshot=policy_snapshot,
                )
            )
            source_key = space_ctx.store_key_for(from_space)
            source_owner = space_ctx.owner_for(from_space)
            source_phase = phase_registry.current(source_key) or session_phase
            removed = None
            if item.kind == MemoryKind.SEMANTIC:
                removed = semantic.delete_item(source_key, item.id)
            elif item.kind == MemoryKind.PROFILE:
                removed = profile.delete_item(source_key, item.id)
            if removed and source_phase:
                events.append(
                    build_deleted_event(
                        ai_profile,
                        session,
                        space=from_space,
                        owner=source_owner,
                        phase=source_phase,
                        item=removed,
                        reason="promoted",
                        policy_snapshot=phase_policy_snapshot,
                        replaced_by=stored_item.id,
                    )
                )
                phase_ledger.record_delete(source_key, phase=source_phase, memory_id=removed.id)
    return promoted, events


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
            )
        )
    return phase, events


def _build_phase_diff_events(
    *,
    ai_profile: str,
    session: str,
    diff_request: PhaseDiffRequest,
    space_ctx: SpaceContext,
    contract: MemoryPolicyContract,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
) -> list[dict]:
    events: list[dict] = []
    decision = evaluate_phase_diff(contract.phase)
    border = evaluate_border_read(contract, space=diff_request.space)
    allowed = decision.allowed and border.allowed
    reason = decision.reason if not decision.allowed else border.reason
    events.append(
        build_border_event(
            ai_profile=ai_profile,
            session=session,
            action="phase_diff",
            from_space=diff_request.space,
            to_space=None,
            allowed=allowed,
            reason=reason,
            subject_id=None,
            policy_snapshot={"phase": contract.phase.as_dict()},
        )
    )
    if not allowed:
        return events
    store_key = space_ctx.store_key_for(diff_request.space)
    owner = space_ctx.owner_for(diff_request.space)
    diff = diff_phases(
        phase_ledger,
        store_key=store_key,
        from_phase_id=diff_request.from_phase_id,
        to_phase_id=diff_request.to_phase_id,
    )
    events.append(
        build_memory_phase_diff(
            ai_profile=ai_profile,
            session=session,
            space=diff_request.space,
            owner=owner,
            from_phase_id=diff.from_phase_id,
            to_phase_id=diff.to_phase_id,
            added_count=len(diff.added),
            deleted_count=len(diff.deleted),
            replaced_count=len(diff.replaced),
            top_changes=diff.top_changes(),
            summary_lines=diff.summary_lines(),
        )
    )
    return events


__all__ = ["record_interaction_with_events"]
