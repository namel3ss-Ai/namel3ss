from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryItem
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta
from namel3ss.runtime.memory_agreement import ProposalStore, build_proposed_event, proposal_required
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_rules import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_PROPOSE_TEAM_MEMORY,
    enforce_action,
    merge_required_approvals,
)
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from namel3ss.runtime.memory_trust import (
    build_trust_check_event,
    build_trust_rules_event,
    can_propose,
    required_approvals,
)
from namel3ss.runtime.memory_trust.model import TRUST_OWNER


def _maybe_propose_promotion(
    *,
    ai_profile: str,
    session: str,
    item: MemoryItem,
    reason: str,
    target_lane: str,
    target_phase,
    team_id: str | None,
    actor_id: str,
    actor_level: str,
    trust_rules,
    team_rules,
    contract: MemoryPolicyContract,
    agreements: ProposalStore,
    events: list[dict],
    trust_rules_emitted: bool,
    agreement_defaults: dict | None = None,
) -> tuple[bool, bool]:
    if not proposal_required(target_lane):
        return False, trust_rules_emitted
    event_type = item.meta.get("event_type", EVENT_CONTEXT)
    rule_check = enforce_action(
        rules=team_rules,
        action=ACTION_PROPOSE_TEAM_MEMORY,
        actor_level=actor_level,
        event_type=event_type,
    )
    if rule_check.applied:
        for applied in rule_check.applied:
            events.append(
                build_rule_applied_event(
                    ai_profile=ai_profile,
                    session=session,
                    applied=applied,
                )
            )
    if not rule_check.allowed:
        return True, trust_rules_emitted
    if not trust_rules_emitted and team_id:
        events.append(
            build_trust_rules_event(
                ai_profile=ai_profile,
                session=session,
                team_id=team_id,
                rules=trust_rules,
            )
        )
        trust_rules_emitted = True
    proposal_actor_id = actor_id if actor_id != "anonymous" else str(item.source)
    decision = can_propose(actor_level, trust_rules)
    events.append(
        build_trust_check_event(
            ai_profile=ai_profile,
            session=session,
            action="propose",
            actor_id=proposal_actor_id,
            actor_level=decision.actor_level,
            required_level=decision.required_level,
            allowed=decision.allowed,
            reason=decision.reason,
        )
    )
    if not decision.allowed:
        return True, trust_rules_emitted
    proposal_meta = dict(item.meta)
    proposal_meta["lane"] = target_lane
    proposal_meta["visible_to"] = "team"
    proposal_meta["can_change"] = False
    proposal_meta = ensure_lane_meta(
        proposal_meta,
        lane=target_lane,
        visible_to="team",
        can_change=False,
        allow_team_change=contract.lanes.team_can_change,
    )
    proposal_item = replace(item, meta=proposal_meta)
    rule_approval_check = enforce_action(
        rules=team_rules,
        action=ACTION_APPROVE_TEAM_MEMORY,
        actor_level=TRUST_OWNER,
        event_type=event_type,
    )
    approvals_required = merge_required_approvals(
        _agreement_approval_count(trust_rules, agreement_defaults),
        rule_approval_check.required_approvals,
    )
    proposal = agreements.create_proposal(
        team_id=team_id or "unknown",
        phase_id=target_phase.phase_id,
        memory_item=proposal_item,
        proposed_by=proposal_actor_id,
        reason_code=reason,
        approval_count_required=approvals_required,
        owner_override=_agreement_owner_override(trust_rules, agreement_defaults),
        ai_profile=ai_profile,
    )
    events.append(
        build_proposed_event(
            ai_profile=ai_profile,
            session=session,
            proposal=proposal,
            memory_id=item.id,
            lane=target_lane,
        )
    )
    return True, trust_rules_emitted


def _agreement_approval_count(trust_rules, agreement_defaults: dict | None) -> int:
    if agreement_defaults and agreement_defaults.get("approval_count_required") is not None:
        return int(agreement_defaults.get("approval_count_required"))
    return required_approvals(trust_rules)


def _agreement_owner_override(trust_rules, agreement_defaults: dict | None) -> bool:
    if agreement_defaults and agreement_defaults.get("owner_override") is not None:
        return bool(agreement_defaults.get("owner_override"))
    return bool(getattr(trust_rules, "owner_override", True))


__all__ = ["_maybe_propose_promotion"]
