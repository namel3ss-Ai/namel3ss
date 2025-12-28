from __future__ import annotations

from typing import Callable

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.events import EVENT_CORRECTION, EVENT_FACT
from namel3ss.runtime.memory.helpers import (
    authority_for_source,
    build_conflict_event,
    build_deleted_event,
    build_denied_event,
    build_meta,
    should_attempt_profile,
    should_attempt_semantic,
    with_policy_tags,
)
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION
from namel3ss.runtime.memory_links import (
    LINK_TYPE_CONFLICTS_WITH,
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
)
from namel3ss.runtime.memory_policy.evaluation import evaluate_write
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger

from .analytics import _build_change_preview_event
from .utils import _phase_id_for_item


def _write_semantic_from_user(
    *,
    ai_profile: str,
    session: str,
    user_input: str,
    user_event_type: str,
    user_importance: int,
    user_reasons: list[str],
    promotion_target: str | None,
    promotion_reason: str | None,
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
    if not policy.semantic_enabled or not should_attempt_semantic(user_event_type, user_input, policy.write_policy):
        return
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
    if write_allowed(semantic_item, lane=session_lane):
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
                            space="session",
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


def _write_profile_from_fact(
    *,
    ai_profile: str,
    session: str,
    user_input: str,
    user_event_type: str,
    fact,
    is_correction: bool,
    stored_user: MemoryItem | None,
    user_importance: int,
    user_reasons: list[str],
    promotion_target: str | None,
    promotion_reason: str | None,
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
    if not policy.profile_enabled or not fact or not should_attempt_profile(user_event_type):
        return
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
    if write_allowed(profile_item, lane=session_lane):
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
                            space="session",
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
