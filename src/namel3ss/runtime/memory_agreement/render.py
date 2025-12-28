from __future__ import annotations

from namel3ss.runtime.memory_agreement.model import AgreementCounts, AgreementSummary, Proposal
from namel3ss.runtime.memory_links.preview import preview_text


def proposal_title(proposal: Proposal) -> str:
    event_type = _event_type(proposal)
    if event_type:
        return f"Team proposal {event_type}"
    return "Team memory proposal"


def proposed_lines(proposal: Proposal) -> list[str]:
    lines = ["Team memory proposal created."]
    lines.extend(_proposal_identity_lines(proposal))
    lines.append(f"Approvals required is {proposal.approval_count_required}.")
    preview = _preview_text(proposal)
    if preview:
        lines.append(f"Preview is {preview}.")
    lines.append(_status_line(proposal))
    return lines


def approved_lines(proposal: Proposal, *, memory_id: str) -> list[str]:
    lines = ["Team memory proposal approved."]
    lines.extend(_proposal_identity_lines(proposal))
    lines.append(f"Memory id is {memory_id}.")
    lines.append(_status_line(proposal))
    return lines


def rejected_lines(proposal: Proposal, *, reason: str | None = None) -> list[str]:
    lines = ["Team memory proposal rejected."]
    lines.extend(_proposal_identity_lines(proposal))
    if reason:
        lines.append(f"Reason is {reason}.")
    lines.append(_status_line(proposal))
    return lines


def agreement_summary(counts: AgreementCounts) -> AgreementSummary:
    lines: list[str] = []
    if counts.approved:
        lines.append(_count_line(counts.approved, "proposal was approved", "proposals were approved"))
    if counts.rejected:
        lines.append(_count_line(counts.rejected, "proposal was rejected", "proposals were rejected"))
    if counts.pending:
        lines.append(_count_line(counts.pending, "proposal is waiting", "proposals are waiting"))
    if not lines:
        lines.append("No proposals changed.")
    return AgreementSummary(title="Team agreement summary", lines=lines)


def proposal_payload(proposal: Proposal) -> dict:
    approvals = list(proposal.approvals)
    return {
        "proposal_id": proposal.proposal_id,
        "memory_id": proposal.memory_item.id,
        "title": proposal_title(proposal),
        "status": proposal.status,
        "proposed_by": proposal.proposed_by,
        "phase_id": proposal.phase_id,
        "event_type": _event_type(proposal),
        "preview": _preview_text(proposal),
        "approval_count": len(approvals),
        "approval_required": proposal.approval_count_required,
        "approvers": approvals,
        "status_line": _status_line(proposal),
        "ai_profile": proposal.ai_profile,
    }


def _proposal_identity_lines(proposal: Proposal) -> list[str]:
    lines = [
        f"Proposal id is {proposal.proposal_id}.",
        f"Phase is {proposal.phase_id}.",
        f"Proposed by is {proposal.proposed_by}.",
    ]
    event_type = _event_type(proposal)
    if event_type:
        lines.append(f"Event type is {event_type}.")
    return lines


def _event_type(proposal: Proposal) -> str | None:
    meta = proposal.memory_item.meta or {}
    event_type = meta.get("event_type")
    if isinstance(event_type, str) and event_type:
        return event_type
    return None


def _preview_text(proposal: Proposal) -> str:
    return preview_text(proposal.memory_item.text)


def _count_line(count: int, singular: str, plural: str) -> str:
    if count == 1:
        return f"One {singular}."
    return f"{count} {plural}."


def _status_line(proposal: Proposal) -> str:
    status = proposal.status
    if status == "approved":
        return "Status is approved."
    if status == "rejected":
        return "Status is rejected."
    count_now = len(proposal.approvals)
    remaining = proposal.approval_count_required - count_now
    if remaining == 1:
        return "Status is waiting for one more approval."
    if remaining > 1:
        return "Status is waiting for more approvals."
    return "Status is pending."


__all__ = [
    "agreement_summary",
    "approved_lines",
    "proposal_title",
    "proposal_payload",
    "proposed_lines",
    "rejected_lines",
]
