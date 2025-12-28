from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.runtime.memory.contract import MemoryItem


AGREEMENT_PENDING = "pending"
AGREEMENT_APPROVED = "approved"
AGREEMENT_REJECTED = "rejected"

AGREEMENT_STATUSES = {AGREEMENT_PENDING, AGREEMENT_APPROVED, AGREEMENT_REJECTED}


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    memory_item: MemoryItem
    team_id: str
    phase_id: str
    status: str
    proposed_by: str
    proposed_at: int
    approvals: list[str] = field(default_factory=list)
    approval_count_required: int = 1
    owner_override: bool = True
    reason_code: str | None = None
    ai_profile: str | None = None


@dataclass(frozen=True)
class AgreementSummary:
    title: str
    lines: list[str]


@dataclass(frozen=True)
class AgreementCounts:
    approved: int
    rejected: int
    pending: int


__all__ = [
    "AGREEMENT_APPROVED",
    "AGREEMENT_PENDING",
    "AGREEMENT_REJECTED",
    "AGREEMENT_STATUSES",
    "AgreementCounts",
    "AgreementSummary",
    "Proposal",
]
