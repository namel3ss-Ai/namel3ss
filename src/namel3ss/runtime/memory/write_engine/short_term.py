from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.helpers import (
    build_deleted_event,
    build_deleted_events,
    build_forget_events,
)
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SPACE_SESSION
from namel3ss.runtime.memory_links import (
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
)
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger

from .analytics import _build_change_preview_event
from .utils import _phase_id_for_item


def _apply_short_term_summary(
    *,
    ai_profile: str,
    session: str,
    short_term: ShortTermMemory,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    session_key: str,
    session_owner: str,
    session_lane: str,
    session_phase,
    semantic,
    profile,
    link_tracker: LinkTracker,
    phase_ledger: PhaseLedger,
    phase_policy_snapshot: dict,
    events: list[dict],
    written: list[MemoryItem],
) -> None:
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
