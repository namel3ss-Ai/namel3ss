from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory.helpers import (
    build_border_event,
    build_conflict_event,
    build_deleted_event,
)
from namel3ss.runtime.memory_lanes.model import (
    LANE_AGENT,
    LANE_MY,
    LANE_SYSTEM,
    LANE_TEAM,
    agent_lane_key,
    ensure_lane_meta,
    lane_for_space,
)
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
from namel3ss.runtime.memory_agreement import ProposalStore
from namel3ss.runtime.memory_policy.evaluation import evaluate_lane_promotion, evaluate_promotion
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_rules import (
    ACTION_PROMOTE_TO_SYSTEM_LANE,
    ACTION_PROMOTE_TO_TEAM_LANE,
    RULE_SCOPE_SYSTEM,
    RULE_SCOPE_TEAM,
    enforce_action,
)
from namel3ss.runtime.memory_rules.store import active_rules_for_scope
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_timeline.versioning import apply_phase_meta
from namel3ss.traces.builders import build_memory_promoted, build_memory_promotion_denied

from .analytics import _build_change_preview_event
from .budget_guard import budget_allows
from .phases import _ensure_phase_for_store
from .promotions_proposals import _maybe_propose_promotion
from .utils import _phase_id_for_item


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
    agent_id: str | None,
    budget_enforcer,
    agreement_defaults: dict | None = None,
) -> tuple[list[MemoryItem], list[dict]]:
    promoted: list[MemoryItem] = []
    events: list[dict] = []
    if not items:
        return promoted, events
    policy_snapshot = contract.as_dict()
    phase_policy_snapshot = {"phase": contract.phase.as_dict()}
    trust_rules_emitted = False
    team_rules = active_rules_for_scope(semantic=semantic, space_ctx=space_ctx, scope=RULE_SCOPE_TEAM)
    system_rules = active_rules_for_scope(semantic=semantic, space_ctx=space_ctx, scope=RULE_SCOPE_SYSTEM)
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
        if to_space == SPACE_PROJECT and agent_id:
            target_lane = LANE_AGENT
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
        if target_lane == LANE_AGENT:
            target_key = agent_lane_key(space_ctx, space=to_space, agent_id=agent_id or "")
        else:
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
        handled, trust_rules_emitted = _maybe_propose_promotion(
            ai_profile=ai_profile,
            session=session,
            item=item,
            reason=request.reason,
            target_lane=target_lane,
            target_phase=target_phase,
            team_id=team_id,
            actor_id=actor_id,
            actor_level=actor_level,
            trust_rules=trust_rules,
            team_rules=team_rules,
            contract=contract,
            agreements=agreements,
            events=events,
            trust_rules_emitted=trust_rules_emitted,
            agreement_defaults=agreement_defaults,
        )
        if handled:
            continue
        if target_lane == LANE_TEAM:
            event_type = item.meta.get("event_type", EVENT_CONTEXT)
            rule_check = enforce_action(
                rules=team_rules,
                action=ACTION_PROMOTE_TO_TEAM_LANE,
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
                continue
        if target_lane == LANE_SYSTEM:
            event_type = item.meta.get("event_type", EVENT_CONTEXT)
            rule_check = enforce_action(
                rules=system_rules,
                action=ACTION_PROMOTE_TO_SYSTEM_LANE,
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
            agent_id=agent_id if target_lane == LANE_AGENT else None,
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
        if not budget_allows(
            budget_enforcer,
            store_key=target_key,
            space=to_space,
            owner=target_owner,
            lane=target_lane,
            phase=target_phase,
            kind=promoted_item.kind.value,
        ):
            continue
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
