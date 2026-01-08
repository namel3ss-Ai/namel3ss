from __future__ import annotations

from namel3ss.agents.orchestration.policies import MergeOutcome
from namel3ss.traces.builders import (
    build_agent_merge_candidate,
    build_agent_merge_rejected,
    build_agent_merge_selected,
    build_agent_merge_started,
    build_agent_merge_summary,
)
from namel3ss.utils.numbers import decimal_to_str


def build_merge_trace_events(outcome: MergeOutcome, merge_policy) -> list[dict]:
    policy = outcome.policy
    events: list[dict] = []
    candidates = outcome.evaluations
    selected = set(outcome.selected)
    start_lines = [
        f"Merge policy is {policy}.",
        f"Candidate count is {len(candidates)}.",
    ]
    if policy == "ranked" and getattr(merge_policy, "score_key", None):
        start_lines.append(f"Score key is {merge_policy.score_key}.")
    if policy == "ranked" and getattr(merge_policy, "score_rule", None):
        start_lines.append(f"Score rule is {merge_policy.score_rule}.")
    if policy == "consensus" and getattr(merge_policy, "min_consensus", None):
        start_lines.append(f"Consensus threshold is {merge_policy.min_consensus}.")
    events.append(
        build_agent_merge_started(
            policy=policy,
            candidate_count=len(candidates),
            title="Agent merge started",
            lines=start_lines,
        )
    )
    for idx, evaluation in enumerate(candidates):
        lines = []
        status = "valid" if evaluation.valid else "invalid"
        if evaluation.score is not None:
            lines.append(f"Score is {decimal_to_str(evaluation.score)}.")
        if evaluation.reasons:
            lines.extend(evaluation.reasons)
        if not lines:
            lines.append("Candidate passed validation.")
        events.append(
            build_agent_merge_candidate(
                policy=policy,
                agent_name=evaluation.agent_name,
                status=status,
                score=decimal_to_str(evaluation.score) if evaluation.score is not None else None,
                title="Agent merge candidate",
                lines=lines,
            )
        )
        if idx in selected:
            events.append(
                build_agent_merge_selected(
                    policy=policy,
                    agent_name=evaluation.agent_name,
                    score=decimal_to_str(evaluation.score) if evaluation.score is not None else None,
                    title="Agent merge selected",
                    lines=_selected_lines(evaluation),
                )
            )
        else:
            events.append(
                build_agent_merge_rejected(
                    policy=policy,
                    agent_name=evaluation.agent_name,
                    score=decimal_to_str(evaluation.score) if evaluation.score is not None else None,
                    title="Agent merge rejected",
                    lines=_rejected_lines(evaluation),
                )
            )
    summary_lines = _summary_lines(outcome)
    events.append(
        build_agent_merge_summary(
            policy=policy,
            selected_agents=_selected_agents(outcome),
            rejected_agents=_rejected_agents(outcome),
            title="Agent merge summary",
            lines=summary_lines,
        )
    )
    return events


def _selected_agents(outcome: MergeOutcome) -> list[str]:
    return [outcome.evaluations[idx].agent_name for idx in outcome.selected if idx < len(outcome.evaluations)]


def _rejected_agents(outcome: MergeOutcome) -> list[str]:
    selected = set(outcome.selected)
    return [
        evaluation.agent_name
        for idx, evaluation in enumerate(outcome.evaluations)
        if idx not in selected
    ]


def _summary_lines(outcome: MergeOutcome) -> list[str]:
    selected_agents = _selected_agents(outcome)
    rejected_agents = _rejected_agents(outcome)
    lines = [f"Merge policy is {outcome.policy}."]
    if selected_agents:
        lines.append(f"Selected agents: {', '.join(selected_agents)}.")
    else:
        lines.append("No agents were selected.")
    lines.append(f"Rejected agents count is {len(rejected_agents)}.")
    return lines


def _selected_lines(evaluation) -> list[str]:
    lines = ["Selected by merge policy."]
    if evaluation.score is not None:
        lines.append(f"Score is {decimal_to_str(evaluation.score)}.")
    return lines


def _rejected_lines(evaluation) -> list[str]:
    if evaluation.reasons:
        return list(evaluation.reasons)
    return ["Not selected by merge policy."]


__all__ = ["build_merge_trace_events"]
