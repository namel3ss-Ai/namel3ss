from __future__ import annotations

from typing import Callable

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_RULE, classify_event_type
from namel3ss.runtime.memory.helpers import (
    authority_for_source,
    build_border_event,
    build_conflict_event,
    build_deleted_event,
    build_denied_event,
    build_meta,
    with_policy_tags,
)
from namel3ss.runtime.memory.importance import importance_for_event
from namel3ss.runtime.memory_lanes.context import SystemRuleRequest
from namel3ss.runtime.memory_lanes.model import LANE_SYSTEM
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION, SPACE_SYSTEM, SpaceContext
from namel3ss.runtime.memory_links import (
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
)
from namel3ss.runtime.memory_policy.evaluation import evaluate_write
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger

from .analytics import _build_change_preview_event
from .links import _link_tool_events
from .phases import _ensure_phase_for_store
from .utils import _phase_id_for_item


def _write_tool_events(
    *,
    ai_profile: str,
    session: str,
    tool_events: list[dict],
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    session_key: str,
    session_owner: str,
    session_lane: str,
    session_phase,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    link_tracker: LinkTracker,
    phase_ledger: PhaseLedger,
    policy_snapshot: dict,
    phase_policy_snapshot: dict,
    events: list[dict],
    written: list[MemoryItem],
    write_allowed: Callable[..., bool],
) -> None:
    if not policy.semantic_enabled or not tool_events:
        return
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
    if write_allowed(tool_item, lane=session_lane):
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


def _write_system_rule(
    *,
    ai_profile: str,
    session: str,
    system_rule_request: SystemRuleRequest | None,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    space_ctx: SpaceContext,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    policy_snapshot: dict,
    phase_policy_snapshot: dict,
    events: list[dict],
    written: list[MemoryItem],
    budget_enforcer,
) -> None:
    if not system_rule_request:
        return
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
        if not budget_enforcer.allow_write(
            store_key=system_key,
            space=SPACE_SYSTEM,
            owner=system_owner,
            lane=system_lane,
            phase=system_phase,
            kind=rule_item.kind.value,
            incoming=1,
        ):
            return
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
