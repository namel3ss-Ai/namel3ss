from __future__ import annotations

from namel3ss.runtime.memory_trust.enforce import REASON_ALLOWED, REASON_LEVEL_TOO_LOW, REASON_OWNER_OVERRIDE
from namel3ss.runtime.memory_trust.model import TrustRules


def trust_check_title(action: str) -> str:
    return f"Trust check {action}"


def trust_check_lines(*, action: str, actor_id: str, actor_level: str, required_level: str, allowed: bool, reason: str) -> list[str]:
    lines = [
        f"Action is {action}.",
        f"Actor id is {actor_id}.",
        f"Actor level is {actor_level}.",
        f"Required level is {required_level}.",
        "Allowed is yes." if allowed else "Allowed is no.",
    ]
    reason_text = _reason_text(reason)
    if reason_text:
        lines.append(f"Reason is {reason_text}.")
    return lines


def approval_recorded_lines(
    *,
    proposal_id: str,
    actor_id: str,
    count_now: int,
    count_required: int,
) -> list[str]:
    lines = [
        "Approval recorded.",
        f"Proposal id is {proposal_id}.",
        f"Actor id is {actor_id}.",
        f"Approvals now is {count_now}.",
        f"Approvals required is {count_required}.",
    ]
    status = _approval_status_line(count_now, count_required)
    if status:
        lines.append(status)
    return lines


def trust_rules_title() -> str:
    return "Team trust rules"


def trust_rules_lines(rules: TrustRules) -> list[str]:
    lines = [
        f"Propose requires {rules.who_can_propose}.",
        f"Approve requires {rules.who_can_approve}.",
        f"Reject requires {rules.who_can_reject}.",
        f"Approvals required is {int(rules.approval_count_required)}.",
        "Owner override is on." if rules.owner_override else "Owner override is off.",
    ]
    return lines


def trust_overview_lines(*, actor_id: str, actor_level: str, rules: TrustRules) -> list[str]:
    lines = [
        f"Your id is {actor_id}.",
        f"Your level is {actor_level}.",
    ]
    lines.extend(trust_rules_lines(rules))
    return lines


def _reason_text(reason: str) -> str:
    if reason == REASON_OWNER_OVERRIDE:
        return "owner override"
    if reason == REASON_LEVEL_TOO_LOW:
        return "level too low"
    if reason == REASON_ALLOWED:
        return "allowed by rules"
    return reason or ""


def _approval_status_line(count_now: int, count_required: int) -> str:
    if count_now >= count_required:
        return "Status is approved."
    remaining = count_required - count_now
    if remaining == 1:
        return "Status is waiting for one more approval."
    if remaining > 1:
        return "Status is waiting for more approvals."
    return "Status is pending."


__all__ = [
    "approval_recorded_lines",
    "trust_check_lines",
    "trust_check_title",
    "trust_overview_lines",
    "trust_rules_lines",
    "trust_rules_title",
]
