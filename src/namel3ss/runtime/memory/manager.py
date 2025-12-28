from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.contract import (
    MemoryClock,
    MemoryIdGenerator,
    MemoryItemFactory,
    deterministic_recall_hash,
)
from namel3ss.runtime.memory.policy import MemoryPolicy, build_policy
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.recall_engine import recall_context_with_events as recall_context_with_events_engine
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SpaceContext, resolve_space_context
from namel3ss.runtime.memory_agreement import (
    AgreementRequest,
    ProposalStore,
    agreement_request_from_state,
    proposal_payload,
)
from namel3ss.runtime.memory_lanes.context import resolve_team_id, system_rule_request_from_state
from namel3ss.runtime.memory_impact import compute_impact, impact_request_from_state
from namel3ss.runtime.memory_timeline.diff import phase_diff_request_from_state
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry, phase_request_from_state
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory.write_engine import (
    apply_agreement_action as apply_agreement_action_engine,
    record_interaction_with_events as record_interaction_with_events_engine,
)
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.model import PhasePolicy


class MemoryManager:
    def __init__(self) -> None:
        clock = MemoryClock()
        ids = MemoryIdGenerator()
        factory = MemoryItemFactory(clock=clock, id_generator=ids)
        self._clock = clock
        self._ids = ids
        self._factory = factory
        self._phases = PhaseRegistry(clock=clock)
        self._ledger = PhaseLedger()
        self.agreements = ProposalStore()
        self.short_term = ShortTermMemory(factory=factory)
        self.profile = ProfileMemory(factory=factory)
        self.semantic = SemanticMemory(factory=factory)

    def space_context(
        self,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> SpaceContext:
        return resolve_space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )

    def session_id(
        self,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> str:
        return self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        ).session_id

    def policy_for(self, ai: ir.AIDecl) -> MemoryPolicy:
        return build_policy(short_term=ai.memory.short_term, semantic=ai.memory.semantic, profile=ai.memory.profile)

    def policy_contract_for(self, policy: MemoryPolicy):
        mode = "current_plus_history" if policy.allow_cross_phase_recall else "current_only"
        return default_contract(
            write_policy=policy.write_policy,
            forget_policy=policy.forget_policy,
            phase=PhasePolicy(
                enabled=policy.phase_enabled,
                mode=mode,
                allow_cross_phase_recall=policy.allow_cross_phase_recall,
                max_phases=policy.phase_max_phases,
                diff_enabled=policy.phase_diff_enabled,
            ),
        )

    def policy_snapshot(self, ai: ir.AIDecl) -> dict:
        policy = self.policy_for(ai)
        contract = self.policy_contract_for(policy)
        snapshot = policy.as_trace_dict()
        snapshot.update(contract.as_dict())
        return snapshot

    def recall_context(
        self,
        ai: ir.AIDecl,
        user_input: str,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> dict:
        context, _, _ = self.recall_context_with_events(
            ai,
            user_input,
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        return context

    def recall_context_with_events(
        self,
        ai: ir.AIDecl,
        user_input: str,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> tuple[dict, list[dict], dict]:
        space_ctx = self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        policy = self.policy_for(ai)
        contract = self.policy_contract_for(policy)
        phase_request = phase_request_from_state(state)
        return recall_context_with_events_engine(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            user_input=user_input,
            space_ctx=space_ctx,
            policy=policy,
            contract=contract,
            short_term=self.short_term,
            semantic=self.semantic,
            profile=self.profile,
            clock=self._clock,
            phase_registry=self._phases,
            phase_ledger=self._ledger,
            phase_request=phase_request,
        )

    def record_interaction(
        self,
        ai: ir.AIDecl,
        state: Dict[str, object],
        user_input: str,
        ai_output: str,
        tool_events: List[dict],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> List[dict]:
        written, _ = self.record_interaction_with_events(
            ai,
            state,
            user_input,
            ai_output,
            tool_events,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        return written

    def record_interaction_with_events(
        self,
        ai: ir.AIDecl,
        state: Dict[str, object],
        user_input: str,
        ai_output: str,
        tool_events: List[dict],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> tuple[List[dict], List[dict]]:
        space_ctx = self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        policy = self.policy_for(ai)
        contract = self.policy_contract_for(policy)
        phase_request = phase_request_from_state(state)
        phase_diff_request = phase_diff_request_from_state(state)
        impact_request = impact_request_from_state(state)
        agreement_request = agreement_request_from_state(state)
        team_id = resolve_team_id(project_root=project_root, app_path=app_path, config=None)
        system_rule_request = system_rule_request_from_state(state)
        return record_interaction_with_events_engine(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            user_input=user_input,
            ai_output=ai_output,
            tool_events=tool_events,
            identity=identity,
            state=state,
            space_ctx=space_ctx,
            policy=policy,
            contract=contract,
            short_term=self.short_term,
            semantic=self.semantic,
            profile=self.profile,
            factory=self._factory,
            clock=self._clock,
            phase_registry=self._phases,
            phase_ledger=self._ledger,
            phase_request=phase_request,
            agreement_request=agreement_request,
            agreements=self.agreements,
            phase_diff_request=phase_diff_request,
            impact_request=impact_request,
            team_id=team_id,
            system_rule_request=system_rule_request,
        )

    def compute_impact(self, memory_id: str, *, depth_limit: int = 2, max_items: int = 10):
        return compute_impact(
            memory_id=memory_id,
            short_term=self.short_term,
            semantic=self.semantic,
            profile=self.profile,
            depth_limit=depth_limit,
            max_items=max_items,
        )

    def list_team_proposals(self, team_id: str) -> list[dict]:
        proposals = self.agreements.list_pending(team_id)
        return [proposal_payload(proposal) for proposal in proposals]

    def apply_agreement_action(
        self,
        ai: ir.AIDecl,
        state: Dict[str, object],
        request: AgreementRequest,
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
        team_id: str | None = None,
    ) -> list[dict]:
        space_ctx = self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        policy = self.policy_for(ai)
        contract = self.policy_contract_for(policy)
        phase_request = phase_request_from_state(state)
        session_key = space_ctx.store_key_for("session", lane="my")
        session_phase = self._phases.current(session_key)
        resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
        return apply_agreement_action_engine(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            request=request,
            agreements=self.agreements,
            team_id=resolved_team_id,
            space_ctx=space_ctx,
            policy=policy,
            contract=contract,
            short_term=self.short_term,
            semantic=self.semantic,
            profile=self.profile,
            factory=self._factory,
            phase_registry=self._phases,
            phase_ledger=self._ledger,
            phase_request=phase_request,
            session_phase=session_phase,
            identity=identity,
            state=state,
        )

    def recall_hash(self, items: List[dict]) -> str:
        return deterministic_recall_hash(items)
