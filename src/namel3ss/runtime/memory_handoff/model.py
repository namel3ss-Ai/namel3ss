from __future__ import annotations

from dataclasses import dataclass


HANDOFF_STATUS_PENDING = "pending"
HANDOFF_STATUS_APPLIED = "applied"
HANDOFF_STATUS_REJECTED = "rejected"

HANDOFF_STATUSES = {HANDOFF_STATUS_PENDING, HANDOFF_STATUS_APPLIED, HANDOFF_STATUS_REJECTED}


@dataclass(frozen=True)
class HandoffPacket:
    packet_id: str
    from_agent_id: str
    to_agent_id: str
    team_id: str
    space: str
    phase_id: str
    created_by: str
    created_at: int
    items: list[str]
    summary_lines: list[str]
    status: str


__all__ = [
    "HANDOFF_STATUS_APPLIED",
    "HANDOFF_STATUS_PENDING",
    "HANDOFF_STATUS_REJECTED",
    "HANDOFF_STATUSES",
    "HandoffPacket",
]
