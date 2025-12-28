from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.runtime.memory_lanes.model import LANE_TEAM


ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"

AGREEMENT_ACTIONS = {ACTION_APPROVE, ACTION_REJECT}


@dataclass(frozen=True)
class AgreementRequest:
    action: str
    proposal_id: str | None
    requested_by: str


def proposal_required(lane: str) -> bool:
    return lane == LANE_TEAM


def agreement_request_from_state(state: Mapping[str, object] | None) -> AgreementRequest | None:
    if not isinstance(state, Mapping):
        return None
    action_value = state.get("_memory_agreement_action")
    if not action_value:
        return None
    action = str(action_value).strip().lower()
    if action not in AGREEMENT_ACTIONS:
        return None
    proposal_id = state.get("_memory_agreement_proposal_id")
    requested_by = state.get("_memory_agreement_by") or "user"
    proposal_id_text = str(proposal_id).strip() if proposal_id else None
    return AgreementRequest(
        action=action,
        proposal_id=proposal_id_text if proposal_id_text else None,
        requested_by=str(requested_by),
    )


__all__ = [
    "ACTION_APPROVE",
    "ACTION_REJECT",
    "AGREEMENT_ACTIONS",
    "AgreementRequest",
    "agreement_request_from_state",
    "proposal_required",
]
