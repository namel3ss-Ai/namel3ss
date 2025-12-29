from __future__ import annotations

from namel3ss.runtime.memory.contract import (
    MemoryClock,
    MemoryItem,
    MemoryItemFactory,
    MemoryKind,
)
from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    classify_event_type,
)
from namel3ss.runtime.memory.facts import extract_fact
from namel3ss.runtime.memory.helpers import (
    authority_for_source,
    build_denied_event,
    build_meta,
    with_policy_tags,
)
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory_agreement import AgreementRequest, ProposalStore
from namel3ss.runtime.memory_lanes.context import SystemRuleRequest
from namel3ss.runtime.memory_lanes.model import (
    LANE_MY,
)
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.promotion import infer_promotion_request
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION, SpaceContext
from namel3ss.runtime.memory_links import (
    LinkTracker,
)
from namel3ss.runtime.memory_impact import ImpactRequest
from namel3ss.runtime.memory_timeline.diff import PhaseDiffRequest
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_policy.evaluation import evaluate_write
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_trust_check_event,
    build_trust_rules_event,
    can_change_rules,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)

from .agreements import _apply_agreement_actions
from .budget import BudgetEnforcer
from .finalize import _finalize_interaction
from .phases import _ensure_phase_for_store
from .promotions import _promote_items
from .retention import _apply_retention
from .semantic_profile import _write_profile_from_fact, _write_semantic_from_user
from .short_term import _apply_short_term_summary
from .tools_system import _write_system_rule, _write_tool_events
from .write_gate import _build_write_allowed


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
    budget_configs: list[BudgetConfig] | None,
    agreement_defaults: dict | None,
    agreement_request: AgreementRequest | None,
    agreements: ProposalStore,
    phase_diff_request: PhaseDiffRequest | None,
    impact_request: ImpactRequest | None,
    team_id: str | None,
    system_rule_request: SystemRuleRequest | None,
    agent_id: str | None,
) -> tuple[list[dict], list[dict]]:
    events: list[dict] = []
    written: list[MemoryItem] = []
    link_tracker = LinkTracker(short_term=short_term, semantic=semantic, profile=profile)
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    budget_enforcer = BudgetEnforcer(
        budgets=budget_configs or [],
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        policy_snapshot=policy_snapshot,
        phase_policy_snapshot=phase_policy_snapshot,
        contract=contract,
        ai_profile=ai_profile,
        session=session,
        events=events,
        written=written,
    )
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
    budget_enforcer.reserve(
        store_key=session_key,
        space=SPACE_SESSION,
        owner=session_owner,
        lane=session_lane,
        phase=session_phase,
        kind="short_term",
        incoming=2,
    )
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

    _apply_agreement_actions(
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
        agreement_defaults=agreement_defaults,
        budget_enforcer=budget_enforcer,
        events=events,
    )

    promotion_request = infer_promotion_request(user_input)
    promotion_target = promotion_request.target_space if promotion_request else None
    promotion_reason = promotion_request.reason if promotion_request else None

    _write_allowed = _build_write_allowed(
        ai_profile=ai_profile,
        session=session,
        contract=contract,
        policy_snapshot=policy_snapshot,
        events=events,
        budget_enforcer=budget_enforcer,
        store_key=session_key,
        space=SPACE_SESSION,
        owner=session_owner,
        phase=session_phase,
    )

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

    _apply_short_term_summary(
        ai_profile=ai_profile,
        session=session,
        short_term=short_term,
        policy=policy,
        contract=contract,
        session_key=session_key,
        session_owner=session_owner,
        session_lane=session_lane,
        session_phase=session_phase,
        semantic=semantic,
        profile=profile,
        link_tracker=link_tracker,
        phase_ledger=phase_ledger,
        phase_policy_snapshot=phase_policy_snapshot,
        events=events,
        written=written,
    )

    fact = extract_fact(user_input)
    is_correction = user_event_type == EVENT_CORRECTION
    _write_semantic_from_user(
        ai_profile=ai_profile,
        session=session,
        user_input=user_input,
        user_event_type=user_event_type,
        user_importance=user_importance,
        user_reasons=user_reasons,
        promotion_target=promotion_target,
        promotion_reason=promotion_reason,
        policy=policy,
        contract=contract,
        session_key=session_key,
        session_owner=session_owner,
        session_lane=session_lane,
        session_phase=session_phase,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        link_tracker=link_tracker,
        phase_ledger=phase_ledger,
        policy_snapshot=policy_snapshot,
        phase_policy_snapshot=phase_policy_snapshot,
        events=events,
        written=written,
        write_allowed=_write_allowed,
    )
    _write_profile_from_fact(
        ai_profile=ai_profile,
        session=session,
        user_input=user_input,
        user_event_type=user_event_type,
        fact=fact,
        is_correction=is_correction,
        stored_user=stored_user,
        user_importance=user_importance,
        user_reasons=user_reasons,
        promotion_target=promotion_target,
        promotion_reason=promotion_reason,
        policy=policy,
        contract=contract,
        session_key=session_key,
        session_owner=session_owner,
        session_lane=session_lane,
        session_phase=session_phase,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        link_tracker=link_tracker,
        phase_ledger=phase_ledger,
        policy_snapshot=policy_snapshot,
        phase_policy_snapshot=phase_policy_snapshot,
        events=events,
        written=written,
        write_allowed=_write_allowed,
    )

    _write_tool_events(
        ai_profile=ai_profile,
        session=session,
        tool_events=tool_events,
        policy=policy,
        contract=contract,
        session_key=session_key,
        session_owner=session_owner,
        session_lane=session_lane,
        session_phase=session_phase,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        link_tracker=link_tracker,
        phase_ledger=phase_ledger,
        policy_snapshot=policy_snapshot,
        phase_policy_snapshot=phase_policy_snapshot,
        events=events,
        written=written,
        write_allowed=_write_allowed,
    )

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
        agent_id=agent_id,
        budget_enforcer=budget_enforcer,
        agreement_defaults=agreement_defaults,
    )
    if promoted_items:
        written.extend(promoted_items)
    if promotion_events:
        events.extend(promotion_events)

    _write_system_rule(
        ai_profile=ai_profile,
        session=session,
        system_rule_request=system_rule_request,
        policy=policy,
        contract=contract,
        space_ctx=space_ctx,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        policy_snapshot=policy_snapshot,
        phase_policy_snapshot=phase_policy_snapshot,
        events=events,
        written=written,
        budget_enforcer=budget_enforcer,
    )

    now_tick = clock.current()
    events.extend(
        _apply_retention(
            ai_profile=ai_profile,
            session=session,
            policy=policy,
            contract=contract,
            space_ctx=space_ctx,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            semantic=semantic,
            profile=profile,
            promoted_items=promoted_items,
            now_tick=now_tick,
            phase_policy_snapshot=phase_policy_snapshot,
            agent_id=agent_id,
        )
    )

    normalized = _finalize_interaction(
        ai_profile=ai_profile,
        session=session,
        state=state,
        team_id=team_id,
        contract=contract,
        agreements=agreements,
        phase_diff_request=phase_diff_request,
        impact_request=impact_request,
        space_ctx=space_ctx,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        link_tracker=link_tracker,
        events=events,
        written=written,
    )
    return normalized, events
