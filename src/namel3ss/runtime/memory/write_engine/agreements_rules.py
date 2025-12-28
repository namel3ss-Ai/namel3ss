from __future__ import annotations

from dataclasses import replace

from namel3ss.runtime.memory.contract import MemoryItem, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.helpers import build_conflict_event, build_deleted_event
from namel3ss.runtime.memory_lanes.model import ensure_lane_meta
from namel3ss.runtime.memory.policy import MemoryPolicy
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.spaces import SpaceContext
from namel3ss.runtime.memory_agreement import AGREEMENT_APPROVED, ProposalStore, build_approved_event
from namel3ss.runtime.memory_policy.model import MemoryPolicyContract
from namel3ss.runtime.memory_rules import (
    RULE_SCOPE_TEAM,
    apply_active_rule_meta,
    replace_rules_for_key,
    rule_from_item,
    rule_lane_for_scope,
    rule_space_for_scope,
)
from namel3ss.runtime.memory_rules.traces import build_rule_changed_event
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, PhaseRequest
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger

from .budget_guard import budget_allows
from .phases import _ensure_phase_for_store


def _approve_rule_proposal_impl(
    *,
    ai_profile: str,
    session: str,
    proposal,
    agreements: ProposalStore,
    team_id: str | None,
    space_ctx: SpaceContext,
    policy: MemoryPolicy,
    contract: MemoryPolicyContract,
    semantic: SemanticMemory,
    factory: MemoryItemFactory,
    phase_registry: PhaseRegistry,
    phase_ledger: PhaseLedger,
    phase_request: PhaseRequest | None,
    budget_enforcer,
    reject_proposal,
) -> list[dict]:
    events: list[dict] = []
    meta = proposal.memory_item.meta or {}
    scope = str(meta.get("rule_scope") or RULE_SCOPE_TEAM)
    target_space = rule_space_for_scope(scope)
    target_lane = rule_lane_for_scope(scope)
    target_owner = space_ctx.owner_for(target_space)
    target_key = space_ctx.store_key_for(target_space, lane=target_lane)
    target_phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai_profile,
        session=session,
        space=target_space,
        owner=target_owner,
        store_key=target_key,
        contract=contract,
        phase_registry=phase_registry,
        phase_ledger=phase_ledger,
        request=phase_request,
        default_reason="agreement",
        lane=target_lane,
    )
    events.extend(phase_events)
    rule_item = apply_active_rule_meta(proposal.memory_item, phase=target_phase)
    rule_meta = dict(rule_item.meta)
    rule_meta["space"] = target_space
    rule_meta["owner"] = target_owner
    rule_meta["agreement_status"] = AGREEMENT_APPROVED
    rule_meta["proposal_id"] = proposal.proposal_id
    rule_meta = ensure_lane_meta(
        rule_meta,
        lane=target_lane,
        allow_team_change=contract.lanes.team_can_change,
    )
    rule_item = replace(rule_item, meta=rule_meta)
    if not budget_allows(
        budget_enforcer,
        store_key=target_key,
        space=target_space,
        owner=target_owner,
        lane=target_lane,
        phase=target_phase,
        kind=rule_item.kind.value,
    ):
        return events
    removed_items: list[MemoryItem] = []
    rule_key = rule_meta.get("rule_key")
    if isinstance(rule_key, str) and rule_key:
        existing = semantic.items_for_store(target_key)
        for entry in replace_rules_for_key(items=existing, rule_key=rule_key):
            removed = semantic.delete_item(target_key, entry.id)
            if removed:
                removed_items.append(removed)
                events.append(
                    build_deleted_event(
                        ai_profile,
                        session,
                        space=target_space,
                        owner=target_owner,
                        phase=target_phase,
                        item=removed,
                        reason="replaced",
                        policy_snapshot={"phase": contract.phase.as_dict()},
                        replaced_by=rule_item.id,
                    )
                )
                phase_ledger.record_delete(target_key, phase=target_phase, memory_id=removed.id)
    stored_item = None
    conflict = None
    deleted = None
    if rule_item.kind == MemoryKind.SEMANTIC:
        stored_item, conflict, deleted = semantic.store_item(
            target_key,
            rule_item,
            dedupe_enabled=policy.dedupe_enabled,
            authority_order=contract.authority_order,
        )
    stored_is_new = stored_item is not None and stored_item.id == rule_item.id
    if stored_is_new:
        phase_ledger.record_add(target_key, phase=target_phase, item=stored_item)
    if conflict:
        events.append(build_conflict_event(ai_profile, session, conflict))
        if deleted:
            events.append(
                build_deleted_event(
                    ai_profile,
                    session,
                    space=target_space,
                    owner=target_owner,
                    phase=target_phase,
                    item=deleted,
                    reason="conflict_loser",
                    policy_snapshot={"phase": contract.phase.as_dict()},
                    replaced_by=stored_item.id if stored_item else None,
                )
            )
            phase_ledger.record_delete(target_key, phase=target_phase, memory_id=deleted.id)
    if not stored_is_new:
        events.extend(
            reject_proposal(
                ai_profile=ai_profile,
                session=session,
                proposal=proposal,
                agreements=agreements,
                space_ctx=space_ctx,
                contract=contract,
                phase_registry=phase_registry,
                phase_ledger=phase_ledger,
                phase_request=phase_request,
                reason="conflict_loser" if conflict else "store_failed",
            )
        )
        return events
    added_rules = [rule_from_item(stored_item)]
    removed_rules = [rule_from_item(item) for item in removed_items]
    removed_rules.sort(key=lambda rule: rule.rule_id)
    if added_rules or removed_rules:
        phase_from = removed_rules[0].phase_id if removed_rules else target_phase.phase_id
        events.append(
            build_rule_changed_event(
                ai_profile=ai_profile,
                session=session,
                team_id=team_id or "unknown",
                phase_from=phase_from,
                phase_to=target_phase.phase_id,
                added=added_rules,
                removed=removed_rules,
            )
        )
    approved = agreements.approve(proposal.proposal_id, phase_id=target_phase.phase_id)
    if approved:
        decision_view = replace(approved, phase_id=target_phase.phase_id)
        events.append(
            build_approved_event(
                ai_profile=ai_profile,
                session=session,
                proposal=decision_view,
                memory_id=stored_item.id,
                lane=target_lane,
            )
        )
    return events


__all__ = ["_approve_rule_proposal_impl"]
