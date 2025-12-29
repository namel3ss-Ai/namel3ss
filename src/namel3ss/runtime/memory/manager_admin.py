from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.manager_agreements import (
    apply_agreement_action as apply_agreement_action_impl,
    propose_rule_with_events as propose_rule_with_events_impl,
)
from namel3ss.runtime.memory_agreement import AgreementRequest, proposal_payload
from namel3ss.runtime.memory_impact import compute_impact
from namel3ss.runtime.memory_rules import RuleRequest


class MemoryManagerAdminMixin:
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

    def propose_rule_with_events(
        self,
        ai: ir.AIDecl,
        state: Dict[str, object],
        request: RuleRequest,
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
        team_id: str | None = None,
    ) -> list[dict]:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)
        startup_events = self._consume_startup_events()
        events = propose_rule_with_events_impl(
            self,
            ai,
            state,
            request,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
            team_id=team_id,
            agreement_defaults=self._agreement_defaults_payload(),
        )
        if startup_events:
            events = list(startup_events) + events
        return events

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
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_restored(project_root=project_root, app_path=app_path)
        startup_events = self._consume_startup_events()
        events = apply_agreement_action_impl(
            self,
            ai,
            state,
            request,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
            team_id=team_id,
            agreement_defaults=self._agreement_defaults_payload(),
        )
        if startup_events:
            events = list(startup_events) + events
        return events


__all__ = ["MemoryManagerAdminMixin"]
