from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory.helpers import build_border_event, build_conflict_event, build_deleted_event
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta, lane_for_space
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.promotion import promotion_request_for_item
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_PROJECT, SPACE_SESSION, SpaceContext
from namel3ss.runtime.memory_links import (
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_PROMOTED_FROM,
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
)
from namel3ss.runtime.memory_agreement import (
    AGREEMENT_APPROVED,
    ProposalStore,
    build_approved_event,
    build_rejected_event,
)
from namel3ss.runtime.memory_policy.evaluation import evaluate_lane_promotion, evaluate_promotion
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_rules import is_rule_item
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta
from namel3ss.traces.builders import build_memory_promoted, build_memory_promotion_denied

from .analytics import _build_change_preview_event
from .budget_guard import budget_allows
from .agreements_rules import _approve_rule_proposal_impl
from .phases import _ensure_phase_for_store
from .utils import _phase_id_for_item


def _target_space_for_proposal(proposal) -> str | None:
    request = promotion_request_for_item(proposal.memory_item)
    if request:
        return request.target_space
    return None


def _reject_proposal_impl(
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


def _approve_proposal_impl(
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
    events: list[dict] = []
    if is_rule_item(proposal.memory_item):
        return _approve_rule_proposal_impl(
            ai_profile=ai_profile,
            session=session,
            proposal=proposal,
            agreements=agreements,
            team_id=team_id,
            space_ctx=space_ctx,
            policy=policy,
            contract=contract,
            semantic=semantic,
            factory=factory,
            phase_registry=phase_registry,
            phase_ledger=phase_ledger,
            phase_request=phase_request,
            budget_enforcer=budget_enforcer,
            reject_proposal=_reject_proposal_impl,
        )
    request = promotion_request_for_item(proposal.memory_item)
    if request is None:
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
            _reject_proposal_impl(
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
            _reject_proposal_impl(
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
    if not budget_allows(
        budget_enforcer,
        store_key=target_key,
        space=to_space,
        owner=target_owner,
        lane=target_lane,
        phase=target_phase,
        kind=approved_item.kind.value,
    ):
        return events
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
            _reject_proposal_impl(
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
