from __future__ import annotations

from dataclasses import replace

from namel3ss.ingestion.policy import (
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_REVIEW,
    ACTION_INGESTION_RUN,
    ACTION_INGESTION_SKIP,
    ACTION_RETRIEVAL_INCLUDE_WARN,
    ACTION_UPLOAD_REPLACE,
    PolicyDecision,
    evaluate_ingestion_policy,
)
from namel3ss.traces.schema import TraceEventType

from ..model import DecisionStep


_POLICY_ACTIONS = [
    ACTION_INGESTION_RUN,
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_REVIEW,
    ACTION_INGESTION_SKIP,
    ACTION_RETRIEVAL_INCLUDE_WARN,
    ACTION_UPLOAD_REPLACE,
]


def policy_decisions(
    policy,
    policy_rules: dict[str, dict],
    trace_policy: dict[str, dict],
    identity: dict | None,
) -> tuple[list[DecisionStep], dict[str, PolicyDecision]]:
    steps: list[DecisionStep] = []
    decisions: dict[str, PolicyDecision] = {}
    for action in _POLICY_ACTIONS:
        evaluated = evaluate_ingestion_policy(policy, action, identity)
        trace = trace_policy.get(action)
        decision = evaluated
        source = "policy"
        if trace is not None:
            allowed = trace.get("outcome") == "allowed"
            reason = trace.get("reason") or evaluated.reason
            decision = replace(evaluated, allowed=allowed, reason=reason, source="trace")
            source = "trace"
        decisions[action] = decision
        rule = policy_rules.get(action)
        required = list(decision.required_permissions)
        outcome = {
            "decision": "allowed" if decision.allowed else "denied",
            "reason": decision.reason,
            "required_permissions": required,
            "source": source,
        }
        inputs = {"action": action}
        rules = [rule] if rule else []
        steps.append(
            DecisionStep(
                id=f"policy:{action}",
                category="policy",
                subject=action,
                inputs=inputs,
                rules=rules,
                outcome=outcome,
            )
        )
    return steps, decisions


def policy_rule_map(policy_info: dict) -> dict[str, dict]:
    effective = policy_info.get("effective") if isinstance(policy_info, dict) else None
    if not isinstance(effective, list):
        return {}
    mapping: dict[str, dict] = {}
    for entry in effective:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        if isinstance(action, str) and action:
            mapping[action] = dict(entry)
    return mapping


def policy_trace_outcomes(traces: list[dict]) -> dict[str, dict]:
    outcomes: dict[str, dict] = {}
    for trace in traces:
        if trace.get("type") != TraceEventType.AUTHORIZATION_CHECK:
            continue
        subject = trace.get("subject")
        if not isinstance(subject, str) or not subject.startswith("policy:"):
            continue
        action = subject.split("policy:", 1)[1]
        outcomes[action] = {
            "outcome": trace.get("outcome"),
            "reason": trace.get("reason"),
        }
    return outcomes


__all__ = ["policy_decisions", "policy_rule_map", "policy_trace_outcomes"]
