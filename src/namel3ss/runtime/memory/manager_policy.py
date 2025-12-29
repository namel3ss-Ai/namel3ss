from __future__ import annotations

from dataclasses import replace

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.policy import MemoryPolicy, build_policy
from namel3ss.runtime.memory_policy.defaults import default_contract
from namel3ss.runtime.memory_policy.model import PhasePolicy


class MemoryManagerPolicyMixin:
    def policy_for(self, ai: ir.AIDecl) -> MemoryPolicy:
        return build_policy(short_term=ai.memory.short_term, semantic=ai.memory.semantic, profile=ai.memory.profile)

    def policy_contract_for(self, policy: MemoryPolicy):
        if self._pack_setup is None:
            self._ensure_packs(
                project_root=self._default_project_root,
                app_path=self._default_app_path,
            )
        mode = "current_plus_history" if policy.allow_cross_phase_recall else "current_only"
        phase_policy = PhasePolicy(
            enabled=policy.phase_enabled,
            mode=mode,
            allow_cross_phase_recall=policy.allow_cross_phase_recall,
            max_phases=policy.phase_max_phases,
            diff_enabled=policy.phase_diff_enabled,
        )
        if self._pack_setup is not None and self._pack_overrides(prefix="phase."):
            phase_policy = self._pack_setup.phase
        contract = default_contract(
            write_policy=policy.write_policy,
            forget_policy=policy.forget_policy,
            phase=phase_policy,
        )
        if self._pack_setup is not None:
            if self._pack_overrides(prefix="lanes."):
                contract = replace(contract, lanes=self._pack_setup.lanes)
            if self._pack_overrides(prefix="trust."):
                contract = replace(contract, trust=self._pack_setup.trust)
            if self._pack_overrides(prefix="agreement."):
                self._agreement_defaults = self._pack_setup.agreement
            else:
                self._agreement_defaults = None
        self._trust_rules = contract.trust
        return contract

    def policy_snapshot(self, ai: ir.AIDecl) -> dict:
        policy = self.policy_for(ai)
        contract = self.policy_contract_for(policy)
        snapshot = policy.as_trace_dict()
        snapshot.update(contract.as_dict())
        snapshot["budget"] = {"defaults": [cfg.__dict__ for cfg in self._budgets]}
        return snapshot

    def _agreement_defaults_payload(self) -> dict | None:
        if self._agreement_defaults is None:
            return None
        return {
            "approval_count_required": int(self._agreement_defaults.approval_count_required),
            "owner_override": bool(self._agreement_defaults.owner_override),
        }


__all__ = ["MemoryManagerPolicyMixin"]
