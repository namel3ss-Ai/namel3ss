from __future__ import annotations

from namel3ss.runtime.memory.contract import MemoryItem, normalize_memory_item, validate_memory_item
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SpaceContext, validate_space_rules
from namel3ss.runtime.memory_lanes.model import validate_lane_rules
from namel3ss.runtime.memory_agreement import ProposalStore
from namel3ss.runtime.memory_impact import ImpactRequest
from namel3ss.runtime.memory_rules import (
    active_rules_for_scope,
    build_rules_snapshot_event,
    rule_lane_for_scope,
    rule_space_for_scope,
    rules_snapshot_request_from_state,
)
from namel3ss.runtime.memory_timeline.diff import PhaseDiffRequest
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_links import LinkTracker

from .analytics import _build_impact_events, _build_phase_diff_events
from .links import _build_link_events


def _finalize_interaction(
    *,
    ai_profile: str,
    session: str,
    state: dict | None,
    team_id: str | None,
    contract: MemoryPolicyContract,
    agreements: ProposalStore,
    phase_diff_request: PhaseDiffRequest | None,
    impact_request: ImpactRequest | None,
    space_ctx: SpaceContext,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    short_term: ShortTermMemory,
    semantic: SemanticMemory,
    profile: ProfileMemory,
    link_tracker: LinkTracker,
    events: list[dict],
    written: list[MemoryItem],
) -> list[MemoryItem]:
    snapshot_request = rules_snapshot_request_from_state(state)
    if snapshot_request and team_id:
        scope = snapshot_request.scope
        rules = active_rules_for_scope(semantic=semantic, space_ctx=space_ctx, scope=scope)
        snapshot_space = rule_space_for_scope(scope)
        snapshot_lane = rule_lane_for_scope(scope)
        snapshot_key = space_ctx.store_key_for(snapshot_space, lane=snapshot_lane)
        current_phase = phase_registry.current(snapshot_key)
        phase_id = current_phase.phase_id if current_phase else "phase-unknown"
        events.append(
            build_rules_snapshot_event(
                ai_profile=ai_profile,
                session=session,
                team_id=team_id,
                phase_id=phase_id,
                rules=rules,
            )
        )

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
    return normalized


__all__ = ["_finalize_interaction"]
