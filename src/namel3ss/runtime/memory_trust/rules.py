from __future__ import annotations

from typing import Mapping

from namel3ss.runtime.memory_trust.model import (
    TRUST_APPROVER,
    TRUST_CONTRIBUTOR,
    TRUST_LEVELS,
    TRUST_OWNER,
    TRUST_VIEWER,
    TrustRules,
)


DEFAULT_TRUST_RULES = TrustRules()


def rules_from_contract(contract) -> TrustRules:
    if contract is None:
        return DEFAULT_TRUST_RULES
    rules = getattr(contract, "trust", None)
    if isinstance(rules, TrustRules):
        return normalize_rules(rules)
    return DEFAULT_TRUST_RULES


def normalize_rules(rules: TrustRules) -> TrustRules:
    who_can_propose = _valid_level(rules.who_can_propose, fallback=TRUST_CONTRIBUTOR)
    who_can_approve = _valid_level(rules.who_can_approve, fallback=TRUST_APPROVER)
    who_can_reject = _valid_level(rules.who_can_reject, fallback=TRUST_APPROVER)
    approval_count_required = max(1, int(rules.approval_count_required))
    owner_override = bool(rules.owner_override)
    return TrustRules(
        who_can_propose=who_can_propose,
        who_can_approve=who_can_approve,
        who_can_reject=who_can_reject,
        approval_count_required=approval_count_required,
        owner_override=owner_override,
    )


def rules_from_state(state: Mapping[str, object] | None, base_rules: TrustRules) -> TrustRules | None:
    if not isinstance(state, Mapping):
        return None
    action = state.get("_memory_trust_action")
    if not action or str(action).strip().lower() != "change_rules":
        return None
    propose = _valid_level(state.get("_memory_trust_propose_level"), fallback=base_rules.who_can_propose)
    approve = _valid_level(state.get("_memory_trust_approve_level"), fallback=base_rules.who_can_approve)
    reject = _valid_level(state.get("_memory_trust_reject_level"), fallback=base_rules.who_can_reject)
    approval_count = base_rules.approval_count_required
    approval_value = state.get("_memory_trust_approval_count")
    if approval_value is not None:
        try:
            approval_count = int(approval_value)
        except (TypeError, ValueError):
            approval_count = base_rules.approval_count_required
    owner_override = base_rules.owner_override
    override_value = state.get("_memory_trust_owner_override")
    if override_value is not None:
        owner_override = _bool_value(override_value)
    return normalize_rules(
        TrustRules(
            who_can_propose=propose,
            who_can_approve=approve,
            who_can_reject=reject,
            approval_count_required=approval_count,
            owner_override=owner_override,
        )
    )


def _valid_level(value: str, *, fallback: str = TRUST_VIEWER) -> str:
    text = str(value).strip().lower() if value is not None else ""
    if text in TRUST_LEVELS:
        return text
    if fallback in TRUST_LEVELS:
        return fallback
    return TRUST_VIEWER


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(value)


__all__ = ["DEFAULT_TRUST_RULES", "normalize_rules", "rules_from_contract", "rules_from_state"]
