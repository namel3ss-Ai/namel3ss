from __future__ import annotations

from namel3ss.runtime.memory_agreement.model import AgreementSummary, Proposal
from namel3ss.runtime.memory_agreement.render import (
    approved_lines,
    proposal_title,
    proposed_lines,
    rejected_lines,
)
from namel3ss.runtime.memory_lanes.model import LANE_TEAM
from namel3ss.traces.builders import (
    build_memory_agreement_summary,
    build_memory_approved,
    build_memory_proposed,
    build_memory_rejected,
)


def build_proposed_event(
    *,
    ai_profile: str,
    session: str,
    proposal: Proposal,
    memory_id: str,
    lane: str = LANE_TEAM,
) -> dict:
    return build_memory_proposed(
        ai_profile=ai_profile,
        session=session,
        team_id=proposal.team_id,
        phase_id=proposal.phase_id,
        proposal_id=proposal.proposal_id,
        memory_id=memory_id,
        title=proposal_title(proposal),
        lines=proposed_lines(proposal),
        lane=lane,
    )


def build_approved_event(
    *,
    ai_profile: str,
    session: str,
    proposal: Proposal,
    memory_id: str,
    lane: str = LANE_TEAM,
) -> dict:
    return build_memory_approved(
        ai_profile=ai_profile,
        session=session,
        team_id=proposal.team_id,
        phase_id=proposal.phase_id,
        proposal_id=proposal.proposal_id,
        memory_id=memory_id,
        title="Team memory approved",
        lines=approved_lines(proposal, memory_id=memory_id),
        lane=lane,
    )


def build_rejected_event(
    *,
    ai_profile: str,
    session: str,
    proposal: Proposal,
    reason: str | None = None,
    lane: str = LANE_TEAM,
) -> dict:
    return build_memory_rejected(
        ai_profile=ai_profile,
        session=session,
        team_id=proposal.team_id,
        phase_id=proposal.phase_id,
        proposal_id=proposal.proposal_id,
        title="Team memory rejected",
        lines=rejected_lines(proposal, reason=reason),
        lane=lane,
    )


def build_summary_event(
    *,
    ai_profile: str,
    session: str,
    team_id: str,
    space: str,
    phase_from: str,
    phase_to: str,
    summary: AgreementSummary,
    lane: str = LANE_TEAM,
) -> dict:
    return build_memory_agreement_summary(
        ai_profile=ai_profile,
        session=session,
        team_id=team_id,
        space=space,
        phase_from=phase_from,
        phase_to=phase_to,
        title=summary.title,
        lines=summary.lines,
        lane=lane,
    )


__all__ = [
    "build_approved_event",
    "build_proposed_event",
    "build_rejected_event",
    "build_summary_event",
]
