from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItemFactory
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.promotion import promotion_request_for_item
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SpaceContext
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_lanes.model import LANE_SYSTEM, LANE_TEAM, lane_for_space
from namel3ss.runtime.memory_links import LinkTracker
from namel3ss.runtime.memory_agreement import (
    ACTION_APPROVE,
    ACTION_REJECT,
    AgreementRequest,
    ProposalStore,
)
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_approval_recorded_event,
    build_trust_check_event,
    build_trust_rules_event,
    can_approve,
    can_change_rules,
    can_reject,
    is_owner,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.runtime.memory_rules import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    ACTION_PROMOTE_TO_TEAM_LANE,
    ACTION_REJECT_TEAM_MEMORY,
    RULE_SCOPE_SYSTEM,
    RULE_SCOPE_TEAM,
    enforce_action,
    merge_required_approvals,
)
from namel3ss.runtime.memory_rules.store import active_rules_for_scope
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from .agreements_flow import _approve_proposal_impl, _reject_proposal_impl
from .budget import BudgetEnforcer
from .links import _build_link_events


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
    budget_enforcer,
    agreement_defaults: dict | None = None,
    events: list[dict] | None = None,
) -> list[dict]:
    if events is None:
        events = []
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
    team_rules = active_rules_for_scope(semantic=semantic, space_ctx=space_ctx, scope=RULE_SCOPE_TEAM)
    system_rules = active_rules_for_scope(semantic=semantic, space_ctx=space_ctx, scope=RULE_SCOPE_SYSTEM)
    proposal = agreements.select_pending(team_id, request.proposal_id)
    if proposal is None:
        return events
    if request.action == ACTION_REJECT:
        event_type = proposal.memory_item.meta.get("event_type", EVENT_CONTEXT)
        rule_check = enforce_action(
            rules=team_rules,
            action=ACTION_REJECT_TEAM_MEMORY,
            actor_level=actor_level,
            event_type=event_type,
        )
        if rule_check.applied:
            for applied in rule_check.applied:
                events.append(
                    build_rule_applied_event(
                        ai_profile=ai_profile,
                        session=session,
                        applied=applied,
                    )
                )
        if not rule_check.allowed:
            return events
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
        event_type = proposal.memory_item.meta.get("event_type", EVENT_CONTEXT)
        rule_check = enforce_action(
            rules=team_rules,
            action=ACTION_APPROVE_TEAM_MEMORY,
            actor_level=actor_level,
            event_type=event_type,
        )
        if rule_check.applied:
            for applied in rule_check.applied:
                events.append(
                    build_rule_applied_event(
                        ai_profile=ai_profile,
                        session=session,
                        applied=applied,
                    )
                )
        if not rule_check.allowed:
            return events
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
        target_space = _target_space_for_proposal(proposal)
        target_lane = lane_for_space(target_space) if target_space else None
        if target_lane in {LANE_TEAM, LANE_SYSTEM}:
            action = ACTION_PROMOTE_TO_TEAM_LANE if target_lane == LANE_TEAM else ACTION_PROMOTE_TO_SYSTEM_LANE
            rules = team_rules if target_lane == LANE_TEAM else system_rules
            promote_check = enforce_action(
                rules=rules,
                action=action,
                actor_level=actor_level,
                event_type=event_type,
            )
            if promote_check.applied:
                for applied in promote_check.applied:
                    events.append(
                        build_rule_applied_event(
                            ai_profile=ai_profile,
                            session=session,
                            applied=applied,
                        )
                    )
            if not promote_check.allowed:
                return events
        updated, _ = agreements.record_approval(proposal.proposal_id, actor_id=actor_id)
        if updated is None:
            return events
        count_now = len(updated.approvals)
        count_required = merge_required_approvals(
            updated.approval_count_required, rule_check.required_approvals
        )
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
        if is_owner(actor_level) and _agreement_owner_override(trust_rules, agreement_defaults):
            events.extend(
                _approve_proposal(
                    ai_profile=ai_profile,
                    session=session,
                    proposal=updated,
                    agreements=agreements,
                    team_id=team_id,
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
                    budget_enforcer=budget_enforcer,
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
                team_id=team_id,
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
                budget_enforcer=budget_enforcer,
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
    return _reject_proposal_impl(
        ai_profile=ai_profile,
        session=session,
        proposal=proposal,
        agreements=agreements,
        space_ctx=space_ctx,
        contract=contract,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        phase_request=phase_request,
        reason=reason,
    )


def _approve_proposal(
    *,
    ai_profile: str,
    session: str,
    proposal,
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
    link_tracker: LinkTracker,
    budget_enforcer,
) -> list[dict]:
    return _approve_proposal_impl(
        ai_profile=ai_profile,
        session=session,
        proposal=proposal,
        agreements=agreements,
        team_id=team_id,
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
        budget_enforcer=budget_enforcer,
    )


def _target_space_for_proposal(proposal) -> str | None:
    request = promotion_request_for_item(proposal.memory_item)
    if request:
        return request.target_space
    return None


def _agreement_owner_override(trust_rules, agreement_defaults: dict | None) -> bool:
    if agreement_defaults and agreement_defaults.get("owner_override") is not None:
        return bool(agreement_defaults.get("owner_override"))
    return bool(getattr(trust_rules, "owner_override", True))


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
    budget_configs: list[BudgetConfig] | None = None,
    agreement_defaults: dict | None = None,
) -> list[dict]:
    link_tracker = LinkTracker(short_term=short_term, semantic=semantic, profile=profile)
    events: list[dict] = []
    budget_enforcer = BudgetEnforcer(
        budgets=budget_configs or [],
        short_term=short_term,
        semantic=semantic,
        profile=profile,
        factory=factory,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        policy_snapshot=contract.as_dict(),
        phase_policy_snapshot={"phase": contract.phase.as_dict()},
        contract=contract,
        ai_profile=ai_profile,
        session=session,
        events=events,
        written=[],
    )
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
        agreement_defaults=agreement_defaults,
        events=events,
        budget_enforcer=budget_enforcer,
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
