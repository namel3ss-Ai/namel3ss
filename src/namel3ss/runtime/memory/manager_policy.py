from __future__ import annotations

from dataclasses import replace

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.policy import MemoryPolicy, build_policy
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.model import PhasePolicy


class MemoryManagerPolicyMixin:
    def policy_for(self, ai: ir.AIDecl) -> MemoryPolicy:
        return build_policy(short_term=ai.memory.short_term, semantic=ai.memory.semantic, profile=ai.memory.profile)

    def policy_contract_for(
        self,
        policy: MemoryPolicy,
        *,
        agent_id: str | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ):
        setup = self._pack_setup_for(
            agent_id=agent_id,
            project_root=project_root or self._default_project_root,
            app_path=app_path or self._default_app_path,
        )
        mode = "current_plus_history" if policy.allow_cross_phase_recall else "current_only"
        phase_policy = PhasePolicy(
            enabled=policy.phase_enabled,
            mode=mode,
            allow_cross_phase_recall=policy.allow_cross_phase_recall,
            max_phases=policy.phase_max_phases,
            diff_enabled=policy.phase_diff_enabled,
        )
        if setup is not None and self._pack_overrides_for(setup, prefix="phase."):
            phase_policy = setup.phase
        contract = default_contract(
            write_policy=policy.write_policy,
            forget_policy=policy.forget_policy,
            phase=phase_policy,
        )
        if setup is not None:
            if self._pack_overrides_for(setup, prefix="lanes."):
                contract = replace(contract, lanes=setup.lanes)
            if self._pack_overrides_for(setup, prefix="trust."):
                contract = replace(contract, trust=setup.trust)
        self._trust_rules = contract.trust
        return contract

    def policy_snapshot(
        self,
        ai: ir.AIDecl,
        *,
        agent_id: str | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> dict:
        policy = self.policy_for(ai)
        setup = self._pack_setup_for(
            agent_id=agent_id,
            project_root=project_root or self._default_project_root,
            app_path=app_path or self._default_app_path,
        )
        contract = self.policy_contract_for(
            policy,
            agent_id=agent_id,
            project_root=project_root,
            app_path=app_path,
        )
        snapshot = policy.as_trace_dict()
        snapshot.update(contract.as_dict())
        budgets = setup.budgets if setup is not None else self._budgets
        snapshot["budget"] = {"defaults": [cfg.__dict__ for cfg in budgets]}
        return snapshot

    def _agreement_defaults_payload(self, setup=None) -> dict | None:
        agreement = None
        if setup is not None and self._pack_overrides_for(setup, prefix="agreement."):
            agreement = setup.agreement
        elif self._agreement_defaults is not None:
            agreement = self._agreement_defaults
        if agreement is None:
            return None
        return {
            "approval_count_required": int(agreement.approval_count_required),
            "owner_override": bool(agreement.owner_override),
        }


__all__ = ["MemoryManagerPolicyMixin"]
