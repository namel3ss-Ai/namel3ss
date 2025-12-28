from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.helpers import build_border_event
from namel3ss.runtime.memory_lanes.model import LANE_MY, LANE_TEAM, lane_for_space
from namel3ss.runtime.memory_lanes.summary import build_team_summary
from namel3ss.runtime.memory_links import (
    LINK_TYPE_REPLACED,
    LinkTracker,
    build_link_record,
    build_preview_for_item,
    get_item_by_id,
)
from namel3ss.runtime.memory_agreement import ProposalStore, agreement_summary, build_summary_event
from namel3ss.runtime.memory_impact import ImpactRequest, compute_impact, render_change_preview, render_impact
from namel3ss.runtime.memory_policy.evaluation import evaluate_border_read, evaluate_lane_read, evaluate_phase_diff
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SpaceContext
from namel3ss.runtime.memory_timeline.diff import PhaseDiffRequest, diff_phases
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.traces.builders import (
    build_memory_change_preview,
    build_memory_impact,
    build_memory_phase_diff,
    build_memory_team_summary,
)

from .phases import _phase_ids_between
from .utils import _meta_value


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
