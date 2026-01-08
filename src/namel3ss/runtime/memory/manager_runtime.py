from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.contract import deterministic_recall_hash
from namel3ss.runtime.memory.recall_engine import recall_context_with_events as recall_context_with_events_engine
from namel3ss.runtime.memory.write_engine import (
    record_interaction_with_events as record_interaction_with_events_engine,
)
from namel3ss.runtime.memory_agreement import agreement_request_from_state
from namel3ss.runtime.memory_impact import impact_request_from_state
from namel3ss.runtime.memory_lanes.context import resolve_team_id, system_rule_request_from_state
from namel3ss.runtime.memory_timeline.diff import phase_diff_request_from_state
from namel3ss.runtime.memory_timeline.phase import phase_request_from_state


class MemoryManagerRuntimeMixin:
    def recall_context(
        self,
        ai: ir.AIDecl,
        user_input: str,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
        agent_id: str | None = None,
    ) -> dict:
        context, _, _ = self.recall_context_with_events(
            ai,
            user_input,
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
            agent_id=agent_id,
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
        agent_id: str | None = None,
    ) -> tuple[dict, list[dict], dict]:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)
        startup_events = self._consume_startup_events()
        space_ctx = self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        policy = self.policy_for(ai)
        setup = self._pack_setup_for(agent_id=agent_id, project_root=project_root, app_path=app_path)
        contract = self.policy_contract_for(
            policy,
            agent_id=agent_id,
            project_root=project_root,
            app_path=app_path,
        )
        phase_request = phase_request_from_state(state)
        context, events, meta = recall_context_with_events_engine(
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
            budget_configs=setup.budgets if setup is not None else self._budgets,
            cache_store=self._cache,
            cache_version_for=self._cache_version_for,
            cache_bump=self._bump_cache_version,
            agent_id=agent_id,
        )
        if startup_events:
            events = list(startup_events) + events
        return context, events, meta

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
        agent_id: str | None = None,
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
            agent_id=agent_id,
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
        agent_id: str | None = None,
    ) -> tuple[List[dict], List[dict]]:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)
        startup_events = self._consume_startup_events()
        space_ctx = self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )
        policy = self.policy_for(ai)
        setup = self._pack_setup_for(agent_id=agent_id, project_root=project_root, app_path=app_path)
        contract = self.policy_contract_for(
            policy,
            agent_id=agent_id,
            project_root=project_root,
            app_path=app_path,
        )
        phase_request = phase_request_from_state(state)
        phase_diff_request = phase_diff_request_from_state(state)
        impact_request = impact_request_from_state(state)
        agreement_request = agreement_request_from_state(state)
        team_id = resolve_team_id(project_root=project_root, app_path=app_path, config=None)
        system_rule_request = system_rule_request_from_state(state)
        written, events = record_interaction_with_events_engine(
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
            budget_configs=setup.budgets if setup is not None else self._budgets,
            agreement_defaults=self._agreement_defaults_payload(setup),
            agreement_request=agreement_request,
            agreements=self.agreements,
            phase_diff_request=phase_diff_request,
            impact_request=impact_request,
            team_id=team_id,
            system_rule_request=system_rule_request,
            agent_id=agent_id,
        )
        self._update_cache_versions(written, events)
        if startup_events:
            events = list(startup_events) + events
        return written, events

    def recall_hash(self, items: List[dict]) -> str:
        return deterministic_recall_hash(items)


__all__ = ["MemoryManagerRuntimeMixin"]
