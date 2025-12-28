from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from namel3ss.runtime.memory_agreement.model import (
    AGREEMENT_APPROVED,
    AGREEMENT_PENDING,
    AGREEMENT_REJECTED,
    AgreementCounts,
    Proposal,
)


@dataclass(frozen=True)
class _AgreementRecord:
    proposal_id: str
    status: str
    phase_id: str
    decided_at: int


class ProposalStore:
    def __init__(self) -> None:
        self._counter = 0
        self._tick = 0
        self._pending_by_team: dict[str, dict[str, list[Proposal]]] = {}
        self._pending_by_id: dict[str, Proposal] = {}
        self._history: dict[str, list[_AgreementRecord]] = {}

    def create_proposal(
        self,
        *,
        team_id: str,
        phase_id: str,
        memory_item,
        proposed_by: str,
        reason_code: str | None,
        approval_count_required: int = 1,
        owner_override: bool = True,
        ai_profile: str | None = None,
    ) -> Proposal:
        proposal_id = self._next_id()
        proposed_at = self._next_tick()
        meta = dict(memory_item.meta or {})
        meta["agreement_status"] = AGREEMENT_PENDING
        meta["proposal_id"] = proposal_id
        memory_item = replace(memory_item, meta=meta)
        created = Proposal(
            proposal_id=proposal_id,
            memory_item=memory_item,
            team_id=team_id,
            phase_id=phase_id,
            status=AGREEMENT_PENDING,
            proposed_by=proposed_by,
            proposed_at=proposed_at,
            approvals=[],
            approval_count_required=max(1, int(approval_count_required)),
            owner_override=bool(owner_override),
            reason_code=reason_code,
            ai_profile=ai_profile,
        )
        self._pending_by_id[proposal_id] = created
        team_phases = self._pending_by_team.setdefault(team_id, {})
        team_phases.setdefault(phase_id, []).append(created)
        return created

    def list_pending(self, team_id: str) -> list[Proposal]:
        pending = list(self._iter_pending(team_id))
        pending.sort(key=lambda entry: (entry.proposed_at, entry.proposal_id))
        return pending

    def get_pending(self, proposal_id: str) -> Proposal | None:
        return self._pending_by_id.get(proposal_id)

    def select_pending(self, team_id: str, proposal_id: str | None) -> Proposal | None:
        if proposal_id:
            return self._pending_by_id.get(proposal_id)
        pending = self.list_pending(team_id)
        return pending[0] if pending else None

    def record_approval(self, proposal_id: str, *, actor_id: str) -> tuple[Proposal | None, bool]:
        proposal = self._pending_by_id.get(proposal_id)
        if proposal is None:
            return None, False
        approvals = list(proposal.approvals)
        if actor_id in approvals:
            return proposal, False
        approvals.append(actor_id)
        updated = replace(proposal, approvals=approvals)
        self._pending_by_id[proposal_id] = updated
        self._replace_pending(updated)
        return updated, True

    def approve(self, proposal_id: str, *, phase_id: str) -> Proposal | None:
        proposal = self._pending_by_id.pop(proposal_id, None)
        if proposal is None:
            return None
        self._remove_pending(proposal)
        decided_at = self._next_tick()
        approved = replace(proposal, status=AGREEMENT_APPROVED)
        self._record(proposal.team_id, approved, phase_id, decided_at)
        return approved

    def reject(self, proposal_id: str, *, phase_id: str) -> Proposal | None:
        proposal = self._pending_by_id.pop(proposal_id, None)
        if proposal is None:
            return None
        self._remove_pending(proposal)
        decided_at = self._next_tick()
        rejected = replace(proposal, status=AGREEMENT_REJECTED)
        self._record(proposal.team_id, rejected, phase_id, decided_at)
        return rejected

    def counts_for_phases(self, team_id: str, phase_ids: Iterable[str]) -> AgreementCounts:
        phase_set = {str(phase_id) for phase_id in phase_ids}
        pending = sum(1 for entry in self._iter_pending(team_id) if entry.phase_id in phase_set)
        approved = 0
        rejected = 0
        for record in self._history.get(team_id, []):
            if record.phase_id not in phase_set:
                continue
            if record.status == AGREEMENT_APPROVED:
                approved += 1
            elif record.status == AGREEMENT_REJECTED:
                rejected += 1
        return AgreementCounts(approved=approved, rejected=rejected, pending=pending)

    def _iter_pending(self, team_id: str) -> Iterable[Proposal]:
        phases = self._pending_by_team.get(team_id, {})
        for entries in phases.values():
            for entry in entries:
                yield entry

    def _remove_pending(self, proposal: Proposal) -> None:
        team_phases = self._pending_by_team.get(proposal.team_id, {})
        entries = team_phases.get(proposal.phase_id, [])
        remaining = [entry for entry in entries if entry.proposal_id != proposal.proposal_id]
        if remaining:
            team_phases[proposal.phase_id] = remaining
        elif proposal.phase_id in team_phases:
            team_phases.pop(proposal.phase_id, None)

    def _replace_pending(self, proposal: Proposal) -> None:
        team_phases = self._pending_by_team.get(proposal.team_id, {})
        entries = team_phases.get(proposal.phase_id, [])
        replaced = []
        for entry in entries:
            if entry.proposal_id == proposal.proposal_id:
                replaced.append(proposal)
            else:
                replaced.append(entry)
        team_phases[proposal.phase_id] = replaced

    def _record(self, team_id: str, proposal: Proposal, phase_id: str, decided_at: int) -> None:
        record = _AgreementRecord(
            proposal_id=proposal.proposal_id,
            status=proposal.status,
            phase_id=phase_id,
            decided_at=decided_at,
        )
        self._history.setdefault(team_id, []).append(record)

    def _next_id(self) -> str:
        self._counter += 1
        return f"proposal-{self._counter}"

    def _next_tick(self) -> int:
        self._tick += 1
        return self._tick


__all__ = ["ProposalStore"]
