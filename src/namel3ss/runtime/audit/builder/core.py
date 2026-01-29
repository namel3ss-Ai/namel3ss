from __future__ import annotations

from pathlib import Path
from typing import Iterable

from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, load_ingestion_policy
from namel3ss.ingestion.policy_inspection import inspect_ingestion_policy
from namel3ss.runtime.auth.identity_model import build_identity_summary

from ..model import DecisionModel, DecisionStep
from ..retrieval import build_retrieval_step
from .inputs import build_inputs
from .ingestion import ingestion_decisions, review_decisions
from .outcomes import build_outcomes
from .policy import policy_decisions, policy_rule_map, policy_trace_outcomes
from .uploads import upload_decisions, upload_trace_decisions
from .utils import safe_state, safe_traces


def build_decision_model(
    *,
    state: dict | None,
    traces: Iterable[dict] | None,
    project_root: str | Path | None,
    app_path: str | Path | None,
    policy_decl: object | None,
    identity: dict | None,
    upload_id: str | None,
    query: str | None,
    secret_values: list[str] | None = None,
) -> DecisionModel:
    state_value = safe_state(state)
    trace_items = safe_traces(traces)
    identity_summary = build_identity_summary(identity)

    policy_info = inspect_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    policy = load_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    policy_rules = policy_rule_map(policy_info)
    trace_policy = policy_trace_outcomes(trace_items)

    inputs = build_inputs(
        project_root=project_root,
        app_path=app_path,
        identity=identity_summary,
        upload_id=upload_id,
        query=query,
        state=state_value,
    )

    decisions: list[DecisionStep] = []
    decisions.extend(upload_decisions(state_value, upload_id))
    decisions.extend(upload_trace_decisions(trace_items, upload_id))
    decisions.extend(ingestion_decisions(state_value, upload_id))
    decisions.extend(review_decisions(state_value, trace_items, upload_id))

    policy_steps, policy_decisions_map = policy_decisions(
        policy,
        policy_rules,
        trace_policy,
        identity,
    )
    decisions.extend(policy_steps)

    retrieval_step, retrieval_outcome = build_retrieval_step(
        state_value,
        policy_decisions_map.get(ACTION_RETRIEVAL_INCLUDE_WARN),
        policy_rules.get(ACTION_RETRIEVAL_INCLUDE_WARN),
        query=query,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    if retrieval_step is not None:
        decisions.append(retrieval_step)

    outcomes = build_outcomes(state_value, policy_decisions_map, retrieval_outcome, upload_id)
    return DecisionModel(inputs=inputs, decisions=decisions, policies=policy_info, outcomes=outcomes)


__all__ = ["build_decision_model"]
