from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory.contract import (
    MemoryClock,
    MemoryItem,
    MemoryItemFactory,
    MemoryKind,
    normalize_memory_item,
    validate_memory_item,
)
from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_FACT,
    EVENT_RULE,
    classify_event_type,
)
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
from namel3ss.runtime.memory_agreement import (
    ACTION_APPROVE,
    ACTION_REJECT,
    AgreementRequest,
    AGREEMENT_APPROVED,
    ProposalStore,
    agreement_summary,
    build_approved_event,
    build_proposed_event,
    build_rejected_event,
    build_summary_event,
    proposal_required,
)
from namel3ss.runtime.memory_lanes.context import SystemRuleRequest
from namel3ss.runtime.memory_lanes.model import (
    LANE_MY,
    LANE_SYSTEM,
    LANE_TEAM,
    ensure_lane_meta,
    lane_for_space,
    lanes_for_space,
    validate_lane_rules,
)
from namel3ss.runtime.memory_lanes.summary import build_team_summary
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.promotion import infer_promotion_request, promotion_request_for_item
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_PROJECT, SPACE_SESSION, SPACE_SYSTEM, SpaceContext, validate_space_rules
from namel3ss.runtime.memory_links import (
    LINK_TYPE_CAUSED_BY,
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
    build_preview_for_tool,
    get_item_by_id,
    link_lines,
    path_lines,
)
from namel3ss.runtime.memory_impact import ImpactRequest, compute_impact, render_change_preview, render_impact
from namel3ss.runtime.memory_timeline.diff import PhaseDiffRequest, diff_phases
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta
from namel3ss.runtime.memory_policy.evaluation import (
    evaluate_border_read,
    evaluate_border_write,
    evaluate_lane_promotion,
    evaluate_lane_read,
    evaluate_lane_write,
    evaluate_phase_diff,
    evaluate_phase_start,
    evaluate_promotion,
    evaluate_write,
)
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_approval_recorded_event,
    build_trust_check_event,
    build_trust_rules_event,
    can_approve,
    can_change_rules,
    can_propose,
    can_reject,
    is_owner,
    required_approvals,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.traces.builders import (
    build_memory_change_preview,
    build_memory_impact,
    build_memory_links,
    build_memory_phase_diff,
    build_memory_phase_started,
    build_memory_path,
    build_memory_promoted,
    build_memory_promotion_denied,
    build_memory_team_summary,
)


def record_interaction_with_events(
    *,
    ai_profile: str,
    session: str,
    user_input: str,
    ai_output: str,
    tool_events: list[dict],
    identity: dict | None,
    state: dict | None,
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
    agreement_request: AgreementRequest | None,
    agreements: ProposalStore,
    phase_diff_request: PhaseDiffRequest | None,
    impact_request: ImpactRequest | None,
    team_id: str | None,
    system_rule_request: SystemRuleRequest | None,
) -> tuple[list[dict], list[dict]]:
    events: list[dict] = []
    written: list[MemoryItem] = []
    link_tracker = LinkTracker(short_term=short_term, semantic=semantic, profile=profile)
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    session_owner = space_ctx.owner_for(SPACE_SESSION)
    session_lane = LANE_MY
    session_key = space_ctx.store_key_for(SPACE_SESSION, lane=session_lane)
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
        lane=session_lane,
    )
    events.extend(phase_events)
    trust_rules = rules_from_contract(contract)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    override_rules = rules_from_state(state, trust_rules)
    if override_rules is not None:
        decision = can_change_rules(actor_level, trust_rules)
        events.append(
            build_trust_check_event(
                ai_profile=ai_profile,
                session=session,
                action="change_rules",
                actor_id=actor_id,
                actor_level=decision.actor_level,
                required_level=decision.required_level,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        if decision.allowed:
            trust_rules = override_rules
            if team_id:
                events.append(
                    build_trust_rules_event(
                        ai_profile=ai_profile,
                        session=session,
                        team_id=team_id,
                        rules=trust_rules,
                    )
                )

    agreement_events = _apply_agreement_actions(
        ai_profile=ai_profile,
        session=session,
        request=agreement_request,
        agreements=agreements,
        team_id=team_id,
        identity=identity,
        state=state,
        space_ctx=space_ctx,
        policy=policy,
        contract=contract,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        phase_request=phase_request,
        session_phase=session_phase,
        link_tracker=link_tracker,
    )
    if agreement_events:
        events.extend(agreement_events)

    promotion_request = infer_promotion_request(user_input)
    promotion_target = promotion_request.target_space if promotion_request else None
    promotion_reason = promotion_request.reason if promotion_request else None

    def _write_allowed(item: MemoryItem, *, lane: str) -> bool:
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
                from_lane=lane,
                to_lane=lane,
            )
        )
        lane_decision = evaluate_lane_write(contract, lane=lane, space=SPACE_SESSION)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="lane_write",
                from_space=SPACE_SESSION,
                to_space=SPACE_SESSION,
                allowed=lane_decision.allowed,
                reason=lane_decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
                from_lane=lane,
                to_lane=lane,
            )
        )
        return decision.allowed and lane_decision.allowed

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
        lane=session_lane,
        phase=session_phase,
        promotion_target=promotion_target,
        promotion_reason=promotion_reason,
        allow_team_change=contract.lanes.team_can_change,
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
    if _write_allowed(user_item, lane=session_lane):
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
        lane=session_lane,
        phase=session_phase,
        allow_team_change=contract.lanes.team_can_change,
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
    if _write_allowed(ai_item, lane=session_lane):
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
        lane=session_lane,
    )
    if summary_item:
        phase_ledger.record_add(session_key, phase=session_phase, item=summary_item)
        written.append(summary_item)
    if replaced_summary:
        events.append(
            _build_change_preview_event(
                ai_profile=ai_profile,
                session=session,
                item=replaced_summary,
                change_kind="replace",
                short_term=short_term,
                semantic=semantic,
                profile=profile,
            )
        )
        events.append(
            build_deleted_event(
                ai_profile,
                session,
                space=SPACE_SESSION,
                owner=session_owner,
                phase=session_phase,
                item=replaced_summary,
                reason="replaced",
                policy_snapshot=phase_policy_snapshot,
                replaced_by=summary_item.id if summary_item else None,
            )
        )
        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=replaced_summary.id)
        if summary_item:
            link_tracker.add_link(
                from_id=summary_item.id,
                link=build_link_record(
                    link_type=LINK_TYPE_REPLACED,
                    to_id=replaced_summary.id,
                    reason_code="replaced",
                    created_in_phase_id=_phase_id_for_item(summary_item, session_phase.phase_id),
                ),
                preview=build_preview_for_item(replaced_summary),
            )
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
            lane=session_lane,
            phase=session_phase,
            promotion_target=promotion_target,
            promotion_reason=promotion_reason,
            allow_team_change=contract.lanes.team_can_change,
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
        if _write_allowed(semantic_item, lane=session_lane):
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
                    link_tracker.add_link(
                        from_id=conflict.winner.id,
                        link=build_link_record(
                            link_type=LINK_TYPE_CONFLICTS_WITH,
                            to_id=conflict.loser.id,
                            reason_code=conflict.rule,
                            created_in_phase_id=_phase_id_for_item(conflict.winner, session_phase.phase_id),
                        ),
                        preview=build_preview_for_item(conflict.loser),
                    )
                    if deleted:
                        events.append(
                            _build_change_preview_event(
                                ai_profile=ai_profile,
                                session=session,
                                item=deleted,
                                change_kind="replace",
                                short_term=short_term,
                                semantic=semantic,
                                profile=profile,
                            )
                        )
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="conflict_loser",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
                        if stored_item:
                            link_tracker.add_link(
                                from_id=stored_item.id,
                                link=build_link_record(
                                    link_type=LINK_TYPE_REPLACED,
                                    to_id=deleted.id,
                                    reason_code="conflict_loser",
                                    created_in_phase_id=_phase_id_for_item(stored_item, session_phase.phase_id),
                                ),
                                preview=build_preview_for_item(deleted),
                            )
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
            lane=session_lane,
            phase=session_phase,
            promotion_target=promotion_target,
            promotion_reason=promotion_reason,
            allow_team_change=contract.lanes.team_can_change,
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
        if _write_allowed(profile_item, lane=session_lane):
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
                    link_tracker.add_link(
                        from_id=conflict.winner.id,
                        link=build_link_record(
                            link_type=LINK_TYPE_CONFLICTS_WITH,
                            to_id=conflict.loser.id,
                            reason_code=conflict.rule,
                            created_in_phase_id=_phase_id_for_item(conflict.winner, session_phase.phase_id),
                        ),
                        preview=build_preview_for_item(conflict.loser),
                    )
                    if deleted:
                        events.append(
                            _build_change_preview_event(
                                ai_profile=ai_profile,
                                session=session,
                                item=deleted,
                                change_kind="replace",
                                short_term=short_term,
                                semantic=semantic,
                                profile=profile,
                            )
                        )
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="conflict_loser",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
                        if stored_item:
                            link_tracker.add_link(
                                from_id=stored_item.id,
                                link=build_link_record(
                                    link_type=LINK_TYPE_REPLACED,
                                    to_id=deleted.id,
                                    reason_code="conflict_loser",
                                    created_in_phase_id=_phase_id_for_item(stored_item, session_phase.phase_id),
                                ),
                                preview=build_preview_for_item(deleted),
                            )
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
            lane=session_lane,
            phase=session_phase,
            allow_team_change=contract.lanes.team_can_change,
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
        if _write_allowed(tool_item, lane=session_lane):
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
                    _link_tool_events(
                        link_tracker,
                        stored_item,
                        tool_events,
                        fallback_phase=session_phase.phase_id,
                    )
                if conflict:
                    events.append(build_conflict_event(ai_profile, session, conflict))
                    link_tracker.add_link(
                        from_id=conflict.winner.id,
                        link=build_link_record(
                            link_type=LINK_TYPE_CONFLICTS_WITH,
                            to_id=conflict.loser.id,
                            reason_code=conflict.rule,
                            created_in_phase_id=_phase_id_for_item(conflict.winner, session_phase.phase_id),
                        ),
                        preview=build_preview_for_item(conflict.loser),
                    )
                    if deleted:
                        events.append(
                            _build_change_preview_event(
                                ai_profile=ai_profile,
                                session=session,
                                item=deleted,
                                change_kind="replace",
                                short_term=short_term,
                                semantic=semantic,
                                profile=profile,
                            )
                        )
                        events.append(
                            build_deleted_event(
                                ai_profile,
                                session,
                                space=SPACE_SESSION,
                                owner=session_owner,
                                phase=session_phase,
                                item=deleted,
                                reason="conflict_loser",
                                policy_snapshot=phase_policy_snapshot,
                                replaced_by=stored_item.id if stored_item else None,
                            )
                        )
                        phase_ledger.record_delete(session_key, phase=session_phase, memory_id=deleted.id)
                        if stored_item:
                            link_tracker.add_link(
                                from_id=stored_item.id,
                                link=build_link_record(
                                    link_type=LINK_TYPE_REPLACED,
                                    to_id=deleted.id,
                                    reason_code="conflict_loser",
                                    created_in_phase_id=_phase_id_for_item(stored_item, session_phase.phase_id),
                                ),
                                preview=build_preview_for_item(deleted),
                            )
            else:
                events.append(build_denied_event(ai_profile, session, tool_item, decision, policy_snapshot))

    promoted_items, promotion_events = _promote_items(
        ai_profile=ai_profile,
        session=session,
        items=written,
        agreements=agreements,
        team_id=team_id,
        actor_id=actor_id,
        actor_level=actor_level,
        trust_rules=trust_rules,
        space_ctx=space_ctx,
        policy=policy,
        contract=contract,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        phase_request=phase_request,
        session_phase=session_phase,
        link_tracker=link_tracker,
    )
    if promoted_items:
        written.extend(promoted_items)
    if promotion_events:
        events.extend(promotion_events)

    if system_rule_request:
        system_lane = LANE_SYSTEM
        system_owner = space_ctx.owner_for(SPACE_SYSTEM)
        system_key = space_ctx.store_key_for(SPACE_SYSTEM, lane=system_lane)
        system_phase, system_phase_events = _ensure_phase_for_store(
            ai_profile=ai_profile,
            session=session,
            space=SPACE_SYSTEM,
            owner=system_owner,
            store_key=system_key,
            contract=contract,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            request=None,
            default_reason="system",
            lane=system_lane,
        )
        events.extend(system_phase_events)
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="write",
                from_space=SPACE_SYSTEM,
                to_space=SPACE_SYSTEM,
                allowed=True,
                reason="system_rule",
                subject_id=None,
                policy_snapshot=policy_snapshot,
                from_lane=system_lane,
                to_lane=system_lane,
            )
        )
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="lane_write",
                from_space=SPACE_SYSTEM,
                to_space=SPACE_SYSTEM,
                allowed=True,
                reason="system_rule",
                subject_id=None,
                policy_snapshot=policy_snapshot,
                from_lane=system_lane,
                to_lane=system_lane,
            )
        )
        rule_text = system_rule_request.text
        rule_importance, rule_reasons = importance_for_event(EVENT_RULE, rule_text, "system")
        rule_authority, rule_authority_reason = authority_for_source("system")
        rule_meta = build_meta(
            EVENT_RULE,
            rule_reasons,
            rule_text,
            authority=rule_authority,
            authority_reason=rule_authority_reason,
            space=SPACE_SYSTEM,
            owner=system_owner,
            lane=system_lane,
            phase=system_phase,
            allow_team_change=contract.lanes.team_can_change,
        )
        rule_meta["rule_reason"] = system_rule_request.reason
        rule_item = factory.create(
            session=system_key,
            kind=MemoryKind.SEMANTIC,
            text=rule_text,
            source="system",
            importance=rule_importance,
            meta=rule_meta,
        )
        decision = evaluate_write(contract, rule_item, event_type=EVENT_RULE)
        if decision.allowed:
            rule_item = with_policy_tags(rule_item, decision.tags)
            stored_item, conflict, deleted = semantic.store_item(
                system_key,
                rule_item,
                dedupe_enabled=policy.dedupe_enabled,
                authority_order=contract.authority_order,
            )
            if stored_item and stored_item.id == rule_item.id:
                written.append(stored_item)
                phase_ledger.record_add(system_key, phase=system_phase, item=stored_item)
            if conflict:
                events.append(build_conflict_event(ai_profile, session, conflict))
                if deleted:
                    events.append(
                        _build_change_preview_event(
                            ai_profile=ai_profile,
                            session=session,
                            item=deleted,
                            change_kind="replace",
                            short_term=short_term,
                            semantic=semantic,
                            profile=profile,
                        )
                    )
                    events.append(
                        build_deleted_event(
                            ai_profile,
                            session,
                            space=SPACE_SYSTEM,
                            owner=system_owner,
                            phase=system_phase,
                            item=deleted,
                            reason="conflict_loser",
                            policy_snapshot=phase_policy_snapshot,
                            replaced_by=stored_item.id if stored_item else None,
                        )
                    )
                    phase_ledger.record_delete(system_key, phase=system_phase, memory_id=deleted.id)
        else:
            events.append(build_denied_event(ai_profile, session, rule_item, decision, policy_snapshot))

    now_tick = clock.current()
    spaces_for_retention = _retention_spaces(contract.spaces.read_order, promoted_items)
    for space in spaces_for_retention:
        for lane in lanes_for_space(space, read_order=contract.lanes.read_order):
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

    if phase_diff_request:
        events.extend(
            _build_phase_diff_events(
                ai_profile=ai_profile,
                session=session,
                diff_request=phase_diff_request,
                space_ctx=space_ctx,
                contract=contract,
                agreements=agreements,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                short_term=short_term,
                semantic=semantic,
                profile=profile,
                link_tracker=link_tracker,
                team_id=team_id,
            )
        )

    link_updates = link_tracker.updated_items()
    if link_updates:
        written = [link_updates.get(item.id, item) for item in written]
        events.extend(
            _build_link_events(
                ai_profile=ai_profile,
                session=session,
                items=list(link_updates.values()),
            )
        )

    if impact_request:
        events.extend(
            _build_impact_events(
                ai_profile=ai_profile,
                session=session,
                request=impact_request,
                short_term=short_term,
                semantic=semantic,
                profile=profile,
            )
        )

    normalized = [normalize_memory_item(item) for item in written]
    for item in normalized:
        validate_memory_item(item)
        validate_space_rules(item)
        validate_lane_rules(item)
    return normalized, events


def _promote_items(
    *,
    ai_profile: str,
    session: str,
    items: list[MemoryItem],
    agreements: ProposalStore,
    team_id: str | None,
    actor_id: str,
    actor_level: str,
    trust_rules,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    session_phase,
    link_tracker: LinkTracker,
) -> tuple[list[MemoryItem], list[dict]]:
    promoted: list[MemoryItem] = []
    events: list[dict] = []
    if not items:
        return promoted, events
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    trust_rules_emitted = False
    for item in items:
        if item.kind == MemoryKind.SHORT_TERM:
            continue
        if item.meta.get("promoted_from"):
            continue
        request = promotion_request_for_item(item)
        if not request:
            continue
        from_space = item.meta.get("space", SPACE_SESSION)
        from_lane = item.meta.get("lane", LANE_MY)
        to_space = request.target_space
        target_lane = lane_for_space(to_space)
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
                from_lane=from_lane,
                to_lane=target_lane,
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
                    from_lane=from_lane,
                    to_lane=target_lane,
                )
            )
            continue
        lane_decision = evaluate_lane_promotion(
            contract,
            lane=target_lane,
            space=to_space,
            event_type=item.meta.get("event_type", EVENT_CONTEXT),
        )
        events.append(
            build_border_event(
                ai_profile=ai_profile,
                session=session,
                action="lane_promote",
                from_space=from_space,
                to_space=to_space,
                allowed=lane_decision.allowed,
                reason=lane_decision.reason,
                subject_id=item.id,
                policy_snapshot=policy_snapshot,
                from_lane=from_lane,
                to_lane=target_lane,
            )
        )
        if not lane_decision.allowed:
            events.append(
                build_memory_promotion_denied(
                    ai_profile=ai_profile,
                    session=session,
                    from_space=from_space,
                    to_space=to_space,
                    memory_id=item.id,
                    allowed=False,
                    reason=lane_decision.reason,
                    policy_snapshot=policy_snapshot,
                    from_lane=from_lane,
                    to_lane=target_lane,
                )
            )
            continue
        target_owner = space_ctx.owner_for(to_space)
        target_key = space_ctx.store_key_for(to_space, lane=target_lane)
        target_phase, phase_events = _ensure_phase_for_store(
            ai_profile=ai_profile,
            session=session,
            space=to_space,
            owner=target_owner,
            store_key=target_key,
            contract=contract,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            request=phase_request,
            default_reason="auto",
            lane=target_lane,
        )
        events.extend(phase_events)
        if proposal_required(target_lane):
            if not trust_rules_emitted and team_id:
                events.append(
                    build_trust_rules_event(
                        ai_profile=ai_profile,
                        session=session,
                        team_id=team_id,
                        rules=trust_rules,
                    )
                )
                trust_rules_emitted = True
            proposal_actor_id = actor_id if actor_id != "anonymous" else str(item.source)
            decision = can_propose(actor_level, trust_rules)
            events.append(
                build_trust_check_event(
                    ai_profile=ai_profile,
                    session=session,
                    action="propose",
                    actor_id=proposal_actor_id,
                    actor_level=decision.actor_level,
                    required_level=decision.required_level,
                    allowed=decision.allowed,
                    reason=decision.reason,
                )
            )
            if not decision.allowed:
                continue
            proposal_meta = dict(item.meta)
            proposal_meta["lane"] = target_lane
            proposal_meta["visible_to"] = "team"
            proposal_meta["can_change"] = False
            proposal_meta = ensure_lane_meta(
                proposal_meta,
                lane=target_lane,
                visible_to="team",
                can_change=False,
                allow_team_change=contract.lanes.team_can_change,
            )
            proposal_item = replace(item, meta=proposal_meta)
            proposal = agreements.create_proposal(
                team_id=team_id or "unknown",
                phase_id=target_phase.phase_id,
                memory_item=proposal_item,
                proposed_by=proposal_actor_id,
                reason_code=request.reason,
                approval_count_required=required_approvals(trust_rules),
                owner_override=trust_rules.owner_override,
                ai_profile=ai_profile,
            )
            events.append(
                build_proposed_event(
                    ai_profile=ai_profile,
                    session=session,
                    proposal=proposal,
                    memory_id=item.id,
                    lane=target_lane,
                )
            )
            continue
        promoted_meta = dict(item.meta)
        promoted_meta["space"] = to_space
        promoted_meta["owner"] = target_owner
        promoted_meta["promoted_from"] = item.id
        promoted_meta["promotion_reason"] = request.reason
        promoted_meta["lane"] = target_lane
        promoted_meta.pop("visible_to", None)
        promoted_meta.pop("can_change", None)
        promoted_meta = ensure_lane_meta(
            promoted_meta,
            lane=target_lane,
            allow_team_change=contract.lanes.team_can_change,
        )
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
            link_tracker.add_link(
                from_id=stored_item.id,
                link=build_link_record(
                    link_type=LINK_TYPE_PROMOTED_FROM,
                    to_id=item.id,
                    reason_code=request.reason,
                    created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
                ),
                preview=build_preview_for_item(item),
            )
        if conflict:
            events.append(build_conflict_event(ai_profile, session, conflict))
            link_tracker.add_link(
                from_id=conflict.winner.id,
                link=build_link_record(
                    link_type=LINK_TYPE_CONFLICTS_WITH,
                    to_id=conflict.loser.id,
                    reason_code=conflict.rule,
                    created_in_phase_id=_phase_id_for_item(conflict.winner, target_phase.phase_id),
                ),
                preview=build_preview_for_item(conflict.loser),
            )
            if deleted:
                events.append(
                    _build_change_preview_event(
                        ai_profile=ai_profile,
                        session=session,
                        item=deleted,
                        change_kind="replace",
                        short_term=short_term,
                        semantic=semantic,
                        profile=profile,
                    )
                )
                events.append(
                    build_deleted_event(
                        ai_profile,
                        session,
                        space=to_space,
                        owner=target_owner,
                        phase=target_phase,
                        item=deleted,
                        reason="conflict_loser",
                        policy_snapshot=phase_policy_snapshot,
                        replaced_by=stored_item.id if stored_item else None,
                    )
                )
                phase_ledger.record_delete(target_key, phase=target_phase, memory_id=deleted.id)
                if stored_item:
                    link_tracker.add_link(
                        from_id=stored_item.id,
                        link=build_link_record(
                            link_type=LINK_TYPE_REPLACED,
                            to_id=deleted.id,
                            reason_code="conflict_loser",
                            created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
                        ),
                        preview=build_preview_for_item(deleted),
                    )
        if stored_is_new:
            events.append(
                _build_change_preview_event(
                    ai_profile=ai_profile,
                    session=session,
                    item=item,
                    change_kind="promote",
                    short_term=short_term,
                    semantic=semantic,
                    profile=profile,
                )
            )
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
                    from_lane=from_lane,
                    to_lane=target_lane,
                )
            )
            source_key = space_ctx.store_key_for(from_space, lane=from_lane)
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
                link_tracker.add_link(
                    from_id=stored_item.id,
                    link=build_link_record(
                        link_type=LINK_TYPE_REPLACED,
                        to_id=removed.id,
                        reason_code="promoted",
                        created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
                    ),
                    preview=build_preview_for_item(removed),
                )
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


def _build_phase_diff_events(
    *,
    ai_profile: str,
    session: str,
    diff_request: PhaseDiffRequest,
    space_ctx: SpaceContext,
    contract: MemoryPolicyContract,
    agreements: ProposalStore,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    link_tracker: LinkTracker,
    team_id: str | None,
) -> list[dict]:
    events: list[dict] = []
    lane = diff_request.lane or lane_for_space(diff_request.space)
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
            from_lane=lane,
            to_lane=None,
        )
    )
    if not allowed:
        return events
    lane_decision = evaluate_lane_read(contract, lane=lane, space=diff_request.space)
    events.append(
        build_border_event(
            ai_profile=ai_profile,
            session=session,
            action="lane_read",
            from_space=diff_request.space,
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
        return events
    store_key = space_ctx.store_key_for(diff_request.space, lane=lane)
    owner = space_ctx.owner_for(diff_request.space)
    diff = diff_phases(
        phase_ledger,
        store_key=store_key,
        from_phase_id=diff_request.from_phase_id,
        to_phase_id=diff_request.to_phase_id,
    )
    for before, after, _key in diff.replaced:
        preview = None
        before_item = get_item_by_id(
            short_term=short_term,
            semantic=semantic,
            profile=profile,
            memory_id=before.memory_id,
        )
        if before_item:
            preview = build_preview_for_item(before_item)
        link_tracker.add_link(
            from_id=after.memory_id,
            link=build_link_record(
                link_type=LINK_TYPE_REPLACED,
                to_id=before.memory_id,
                reason_code="phase_diff",
                created_in_phase_id=diff.to_phase_id,
            ),
            preview=preview,
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
            lane=lane,
        )
    )
    if lane == LANE_TEAM and team_id:
        summary = build_team_summary(diff)
        events.append(
            build_memory_team_summary(
                ai_profile=ai_profile,
                session=session,
                team_id=team_id,
                space=diff_request.space,
                phase_from=diff.from_phase_id,
                phase_to=diff.to_phase_id,
                title=summary.title,
                lines=summary.lines,
                lane=lane,
            )
        )
        phase_ids = _phase_ids_between(phase_ledger, store_key, diff.from_phase_id, diff.to_phase_id)
        counts = agreements.counts_for_phases(team_id, phase_ids)
        agreement_summary_value = agreement_summary(counts)
        events.append(
            build_summary_event(
                ai_profile=ai_profile,
                session=session,
                team_id=team_id,
                space=diff_request.space,
                phase_from=diff.from_phase_id,
                phase_to=diff.to_phase_id,
                summary=agreement_summary_value,
                lane=lane,
            )
        )
    return events


def _build_link_events(*, ai_profile: str, session: str, items: list[MemoryItem]) -> list[dict]:
    events: list[dict] = []
    ordered = sorted(items, key=lambda item: item.id)
    for item in ordered:
        links = item.meta.get("links")
        link_count = len(links) if isinstance(links, list) else 0
        if link_count <= 0:
            continue
        phase_id = _phase_id_for_item(item, "phase-unknown")
        space = item.meta.get("space", "session")
        owner = item.meta.get("owner", "anonymous")
        lane = item.meta.get("lane", LANE_MY)
        events.append(
            build_memory_links(
                ai_profile=ai_profile,
                session=session,
                memory_id=item.id,
                phase_id=phase_id,
                space=space,
                owner=owner,
                link_count=link_count,
                lines=link_lines(item),
                lane=lane,
            )
        )
        events.append(
            build_memory_path(
                ai_profile=ai_profile,
                session=session,
                memory_id=item.id,
                phase_id=phase_id,
                space=space,
                owner=owner,
                title="Memory path",
                lines=path_lines(item),
                lane=lane,
            )
        )
    return events


def _build_impact_events(
    *,
    ai_profile: str,
    session: str,
    request: ImpactRequest,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
) -> list[dict]:
    events: list[dict] = []
    root_item = get_item_by_id(short_term=short_term, semantic=semantic, profile=profile, memory_id=request.memory_id)
    space = _meta_value(root_item, "space", "unknown")
    owner = _meta_value(root_item, "owner", "unknown")
    phase_id = _meta_value(root_item, "phase_id", "phase-unknown")
    lane = _meta_value(root_item, "lane", LANE_MY)
    for depth in request.depths:
        result = compute_impact(
            memory_id=request.memory_id,
            short_term=short_term,
            semantic=semantic,
            profile=profile,
            depth_limit=depth,
            max_items=request.max_items,
            root_item=root_item,
        )
        result = render_impact(result, depth_used=depth)
        events.append(
            build_memory_impact(
                ai_profile=ai_profile,
                session=session,
                memory_id=request.memory_id,
                space=space,
                owner=owner,
                phase_id=phase_id,
                depth_used=depth,
                item_count=len(result.items),
                title=result.title,
                lines=result.lines,
                path_lines=result.path_lines,
                lane=lane,
            )
        )
    return events


def _apply_agreement_actions(
    *,
    ai_profile: str,
    session: str,
    request: AgreementRequest | None,
    agreements: ProposalStore,
    team_id: str | None,
    identity: dict | None,
    state: dict | None,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    session_phase,
    link_tracker: LinkTracker,
) -> list[dict]:
    events: list[dict] = []
    if request is None or not team_id:
        return events
    trust_rules = rules_from_contract(contract)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    if actor_id == "anonymous" and request.requested_by:
        actor_id = str(request.requested_by)
    override_rules = rules_from_state(state, trust_rules)
    if override_rules is not None:
        decision = can_change_rules(actor_level, trust_rules)
        events.append(
            build_trust_check_event(
                ai_profile=ai_profile,
                session=session,
                action="change_rules",
                actor_id=actor_id,
                actor_level=decision.actor_level,
                required_level=decision.required_level,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        if decision.allowed:
            trust_rules = override_rules
    events.append(
        build_trust_rules_event(
            ai_profile=ai_profile,
            session=session,
            team_id=team_id,
            rules=trust_rules,
        )
    )
    proposal = agreements.select_pending(team_id, request.proposal_id)
    if proposal is None:
        return events
    if request.action == ACTION_REJECT:
        decision = can_reject(actor_level, trust_rules)
        events.append(
            build_trust_check_event(
                ai_profile=ai_profile,
                session=session,
                action="reject",
                actor_id=actor_id,
                actor_level=decision.actor_level,
                required_level=decision.required_level,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        if not decision.allowed:
            return events
        events.extend(
            _reject_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=proposal,
                agreements=agreements,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
            )
        )
        return events
    if request.action == ACTION_APPROVE:
        decision = can_approve(actor_level, trust_rules)
        events.append(
            build_trust_check_event(
                ai_profile=ai_profile,
                session=session,
                action="approve",
                actor_id=actor_id,
                actor_level=decision.actor_level,
                required_level=decision.required_level,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        if not decision.allowed:
            return events
        updated, _ = agreements.record_approval(proposal.proposal_id, actor_id=actor_id)
        if updated is None:
            return events
        count_now = len(updated.approvals)
        count_required = updated.approval_count_required
        events.append(
            build_approval_recorded_event(
                ai_profile=ai_profile,
                session=session,
                proposal_id=updated.proposal_id,
                actor_id=actor_id,
                count_now=count_now,
                count_required=count_required,
            )
        )
        if is_owner(actor_level) and trust_rules.owner_override:
            events.extend(
                _approve_proposal(
                    ai_profile=ai_profile,
                    session=session,
                    proposal=updated,
                    agreements=agreements,
                    space_ctx=space_ctx,
                    policy=policy,
                    contract=contract,
                    short_term=short_term,
                    semantic=semantic,
                    profile=profile,
                    factory=factory,
                    phase_registry=phase_registry,
                    phase_ledger=phase_ledger,
                    phase_request=phase_request,
                    session_phase=session_phase,
                    link_tracker=link_tracker,
                )
            )
            return events
        if count_now < count_required:
            return events
        events.extend(
            _approve_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=updated,
                agreements=agreements,
                space_ctx=space_ctx,
                policy=policy,
                contract=contract,
                short_term=short_term,
                semantic=semantic,
                profile=profile,
                factory=factory,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
                session_phase=session_phase,
                link_tracker=link_tracker,
            )
        )
        return events
    return events


def _reject_proposal(
    *,
    ai_profile: str,
    session: str,
    proposal,
    agreements: ProposalStore,
    space_ctx: SpaceContext,
    contract: MemoryPolicyContract,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    reason: str | None = None,
) -> list[dict]:
    events: list[dict] = []
    target_space = _target_space_for_proposal(proposal) or SPACE_PROJECT
    target_lane = lane_for_space(target_space)
    target_owner = space_ctx.owner_for(target_space)
    target_key = space_ctx.store_key_for(target_space, lane=target_lane)
    target_phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai_profile,
        session=session,
        space=target_space,
        owner=target_owner,
        store_key=target_key,
        contract=contract,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        request=phase_request,
        default_reason="agreement",
        lane=target_lane,
    )
    events.extend(phase_events)
    rejected = agreements.reject(proposal.proposal_id, phase_id=target_phase.phase_id)
    if rejected:
        decision_view = replace(rejected, phase_id=target_phase.phase_id)
        events.append(
            build_rejected_event(
                ai_profile=ai_profile,
                session=session,
                proposal=decision_view,
                reason=reason,
                lane=target_lane,
            )
        )
    return events


def _approve_proposal(
    *,
    ai_profile: str,
    session: str,
    proposal,
    agreements: ProposalStore,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    session_phase,
    link_tracker: LinkTracker,
) -> list[dict]:
    events: list[dict] = []
    request = promotion_request_for_item(proposal.memory_item)
    if request is None:
        return _reject_proposal(
            ai_profile=ai_profile,
            session=session,
            proposal=proposal,
            agreements=agreements,
            space_ctx=space_ctx,
            contract=contract,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            phase_request=phase_request,
            reason="missing_target",
        )
    from_space = proposal.memory_item.meta.get("space", SPACE_SESSION)
    from_lane = lane_for_space(from_space)
    to_space = request.target_space
    target_lane = lane_for_space(to_space)
    decision = evaluate_promotion(
        contract,
        item=proposal.memory_item,
        from_space=from_space,
        to_space=to_space,
        event_type=proposal.memory_item.meta.get("event_type", EVENT_CONTEXT),
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
            subject_id=proposal.memory_item.id,
            policy_snapshot=contract.as_dict(),
            from_lane=from_lane,
            to_lane=target_lane,
        )
    )
    if not decision.allowed:
        events.append(
            build_memory_promotion_denied(
                ai_profile=ai_profile,
                session=session,
                from_space=from_space,
                to_space=to_space,
                memory_id=proposal.memory_item.id,
                allowed=False,
                reason=decision.reason,
                policy_snapshot=contract.as_dict(),
                from_lane=from_lane,
                to_lane=target_lane,
            )
        )
        events.extend(
            _reject_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=proposal,
                agreements=agreements,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
                reason=decision.reason,
            )
        )
        return events
    lane_decision = evaluate_lane_promotion(
        contract,
        lane=target_lane,
        space=to_space,
        event_type=proposal.memory_item.meta.get("event_type", EVENT_CONTEXT),
    )
    events.append(
        build_border_event(
            ai_profile=ai_profile,
            session=session,
            action="lane_promote",
            from_space=from_space,
            to_space=to_space,
            allowed=lane_decision.allowed,
            reason=lane_decision.reason,
            subject_id=proposal.memory_item.id,
            policy_snapshot=contract.as_dict(),
            from_lane=from_lane,
            to_lane=target_lane,
        )
    )
    if not lane_decision.allowed:
        events.append(
            build_memory_promotion_denied(
                ai_profile=ai_profile,
                session=session,
                from_space=from_space,
                to_space=to_space,
                memory_id=proposal.memory_item.id,
                allowed=False,
                reason=lane_decision.reason,
                policy_snapshot=contract.as_dict(),
                from_lane=from_lane,
                to_lane=target_lane,
            )
        )
        events.extend(
            _reject_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=proposal,
                agreements=agreements,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
                reason=lane_decision.reason,
            )
        )
        return events
    target_owner = space_ctx.owner_for(to_space)
    target_key = space_ctx.store_key_for(to_space, lane=target_lane)
    target_phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai_profile,
        session=session,
        space=to_space,
        owner=target_owner,
        store_key=target_key,
        contract=contract,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        request=phase_request,
        default_reason="agreement",
        lane=target_lane,
    )
    events.extend(phase_events)
    promoted_meta = dict(proposal.memory_item.meta)
    promoted_meta["space"] = to_space
    promoted_meta["owner"] = target_owner
    promoted_meta["promoted_from"] = proposal.memory_item.id
    promoted_meta["promotion_reason"] = request.reason
    promoted_meta["agreement_status"] = AGREEMENT_APPROVED
    promoted_meta["proposal_id"] = proposal.proposal_id
    promoted_meta["lane"] = target_lane
    promoted_meta.pop("visible_to", None)
    promoted_meta.pop("can_change", None)
    promoted_meta = ensure_lane_meta(
        promoted_meta,
        lane=target_lane,
        allow_team_change=contract.lanes.team_can_change,
    )
    promoted_meta = apply_phase_meta(promoted_meta, target_phase)
    approved_item = factory.create(
        session=target_key,
        kind=proposal.memory_item.kind,
        text=proposal.memory_item.text,
        source=proposal.memory_item.source,
        importance=proposal.memory_item.importance,
        meta=promoted_meta,
    )
    conflict = None
    deleted = None
    stored_item = None
    if approved_item.kind == MemoryKind.SEMANTIC:
        stored_item, conflict, deleted = semantic.store_item(
            target_key,
            approved_item,
            dedupe_enabled=policy.dedupe_enabled,
            authority_order=contract.authority_order,
        )
    elif approved_item.kind == MemoryKind.PROFILE:
        stored_item, conflict, deleted = profile.store_item(
            target_key,
            approved_item,
            dedupe_enabled=policy.dedupe_enabled,
            authority_order=contract.authority_order,
        )
    stored_is_new = stored_item is not None and stored_item.id == approved_item.id
    if stored_is_new:
        phase_ledger.record_add(target_key, phase=target_phase, item=stored_item)
        link_tracker.add_link(
            from_id=stored_item.id,
            link=build_link_record(
                link_type=LINK_TYPE_PROMOTED_FROM,
                to_id=proposal.memory_item.id,
                reason_code=request.reason,
                created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
            ),
            preview=build_preview_for_item(proposal.memory_item),
        )
    if conflict:
        events.append(build_conflict_event(ai_profile, session, conflict))
        link_tracker.add_link(
            from_id=conflict.winner.id,
            link=build_link_record(
                link_type=LINK_TYPE_CONFLICTS_WITH,
                to_id=conflict.loser.id,
                reason_code=conflict.rule,
                created_in_phase_id=_phase_id_for_item(conflict.winner, target_phase.phase_id),
            ),
            preview=build_preview_for_item(conflict.loser),
        )
        if deleted:
            events.append(
                _build_change_preview_event(
                    ai_profile=ai_profile,
                    session=session,
                    item=deleted,
                    change_kind="replace",
                    short_term=short_term,
                    semantic=semantic,
                    profile=profile,
                )
            )
            events.append(
                build_deleted_event(
                    ai_profile,
                    session,
                    space=to_space,
                    owner=target_owner,
                    phase=target_phase,
                    item=deleted,
                    reason="conflict_loser",
                    policy_snapshot={"phase": contract.phase.as_dict()},
                    replaced_by=stored_item.id if stored_item else None,
                )
            )
            phase_ledger.record_delete(target_key, phase=target_phase, memory_id=deleted.id)
            if stored_item:
                link_tracker.add_link(
                    from_id=stored_item.id,
                    link=build_link_record(
                        link_type=LINK_TYPE_REPLACED,
                        to_id=deleted.id,
                        reason_code="conflict_loser",
                        created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
                    ),
                    preview=build_preview_for_item(deleted),
                )
    if not stored_is_new:
        events.extend(
            _reject_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=proposal,
                agreements=agreements,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
                reason="conflict_loser" if conflict else "store_failed",
            )
        )
        return events
    events.append(
        _build_change_preview_event(
            ai_profile=ai_profile,
            session=session,
            item=proposal.memory_item,
            change_kind="promote",
            short_term=short_term,
            semantic=semantic,
            profile=profile,
        )
    )
    events.append(
        build_memory_promoted(
            ai_profile=ai_profile,
            session=session,
            from_space=from_space,
            to_space=to_space,
            from_id=proposal.memory_item.id,
            to_id=stored_item.id,
            authority_used=decision.authority_used,
            reason=request.reason,
            policy_snapshot=contract.as_dict(),
            from_lane=from_lane,
            to_lane=target_lane,
        )
    )
    source_key = space_ctx.store_key_for(from_space, lane=from_lane)
    source_owner = space_ctx.owner_for(from_space)
    source_phase = phase_registry.current(source_key) or session_phase
    removed = None
    if approved_item.kind == MemoryKind.SEMANTIC:
        removed = semantic.delete_item(source_key, proposal.memory_item.id)
    elif approved_item.kind == MemoryKind.PROFILE:
        removed = profile.delete_item(source_key, proposal.memory_item.id)
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
                policy_snapshot={"phase": contract.phase.as_dict()},
                replaced_by=stored_item.id,
            )
        )
        phase_ledger.record_delete(source_key, phase=source_phase, memory_id=removed.id)
        link_tracker.add_link(
            from_id=stored_item.id,
            link=build_link_record(
                link_type=LINK_TYPE_REPLACED,
                to_id=removed.id,
                reason_code="promoted",
                created_in_phase_id=_phase_id_for_item(stored_item, target_phase.phase_id),
            ),
            preview=build_preview_for_item(removed),
        )
    approved = agreements.approve(proposal.proposal_id, phase_id=target_phase.phase_id)
    if approved:
        decision_view = replace(approved, phase_id=target_phase.phase_id)
        events.append(
            build_approved_event(
                ai_profile=ai_profile,
                session=session,
                proposal=decision_view,
                memory_id=stored_item.id,
                lane=target_lane,
            )
        )
    return events


def _target_space_for_proposal(proposal) -> str | None:
    request = promotion_request_for_item(proposal.memory_item)
    if request:
        return request.target_space
    return None


def _build_change_preview_event(
    *,
    ai_profile: str,
    session: str,
    item: MemoryItem,
    change_kind: str,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    depth_limit: int = 1,
    max_items: int = 5,
) -> dict:
    result = compute_impact(
        memory_id=item.id,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        depth_limit=depth_limit,
        max_items=max_items,
        root_item=item,
    )
    lines = render_change_preview(result, change_kind=change_kind)
    space = _meta_value(item, "space", "unknown")
    owner = _meta_value(item, "owner", "unknown")
    phase_id = _meta_value(item, "phase_id", "phase-unknown")
    lane = _meta_value(item, "lane", LANE_MY)
    return build_memory_change_preview(
        ai_profile=ai_profile,
        session=session,
        memory_id=item.id,
        change_kind=change_kind,
        title="Memory change preview",
        lines=lines,
        space=space,
        owner=owner,
        phase_id=phase_id,
        lane=lane,
    )


def _phase_id_for_item(item: MemoryItem, fallback: str) -> str:
    meta = item.meta or {}
    phase_id = meta.get("phase_id")
    if isinstance(phase_id, str) and phase_id:
        return phase_id
    return fallback


def _meta_value(item: MemoryItem | None, key: str, fallback: str) -> str:
    if not item:
        return fallback
    meta = item.meta or {}
    value = meta.get(key)
    if isinstance(value, str) and value:
        return value
    return fallback


def _link_tool_events(
    link_tracker: LinkTracker,
    item: MemoryItem,
    tool_events: list[dict],
    *,
    fallback_phase: str,
) -> None:
    if not tool_events:
        return
    phase_id = _phase_id_for_item(item, fallback_phase)
    for entry in tool_events:
        if entry.get("type") != "call":
            continue
        tool_call_id = entry.get("tool_call_id")
        if not tool_call_id:
            continue
        tool_name = entry.get("name") or "tool"
        link_tracker.add_link(
            from_id=item.id,
            link=build_link_record(
                link_type=LINK_TYPE_CAUSED_BY,
                to_id=str(tool_call_id),
                reason_code="tool_call",
                created_in_phase_id=phase_id,
                source_event_id=str(tool_call_id),
            ),
            preview=build_preview_for_tool(str(tool_name)),
        )


def apply_agreement_action(
    *,
    ai_profile: str,
    session: str,
    request: AgreementRequest,
    agreements: ProposalStore,
    team_id: str | None,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    session_phase,
    identity: dict | None,
    state: dict | None,
) -> list[dict]:
    link_tracker = LinkTracker(short_term=short_term, semantic=semantic, profile=profile)
    events = _apply_agreement_actions(
        ai_profile=ai_profile,
        session=session,
        request=request,
        agreements=agreements,
        team_id=team_id,
        state=state,
        space_ctx=space_ctx,
        policy=policy,
        contract=contract,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        phase_request=phase_request,
        session_phase=session_phase,
        link_tracker=link_tracker,
        identity=identity,
    )
    link_updates = link_tracker.updated_items()
    if link_updates:
        events.extend(
            _build_link_events(
                ai_profile=ai_profile,
                session=session,
                items=list(link_updates.values()),
            )
        )
    return events


__all__ = ["apply_agreement_action", "record_interaction_with_events"]
