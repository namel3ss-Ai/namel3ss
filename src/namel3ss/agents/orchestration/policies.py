from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.agents.orchestration.validate import MergeValidator, validate_candidate


POLICY_FIRST_VALID = "first_valid"
POLICY_RANKED = "ranked"
POLICY_CONSENSUS = "consensus"
POLICY_ALL = "all"


@dataclass(frozen=True)
class MergeCandidate:
    agent_name: str
    output: object


@dataclass(frozen=True)
class MergeCandidateEvaluation:
    agent_name: str
    output: object
    valid: bool
    reasons: list[str]
    score: Decimal | None
    consensus_value: str | None


@dataclass(frozen=True)
class MergeOutcome:
    policy: str
    output: object
    selected: list[int]
    evaluations: list[MergeCandidateEvaluation]


def merge_agent_candidates(
    candidates: list[MergeCandidate],
    merge_policy,
    *,
    line: int | None,
    column: int | None,
) -> MergeOutcome:
    policy = getattr(merge_policy, "policy", None)
    if policy not in {POLICY_FIRST_VALID, POLICY_RANKED, POLICY_CONSENSUS, POLICY_ALL}:
        raise Namel3ssError("Unknown merge policy.", line=line, column=column)
    score_key = getattr(merge_policy, "score_key", None)
    score_rule = getattr(merge_policy, "score_rule", None)
    if policy == POLICY_RANKED and not (score_key or score_rule):
        raise Namel3ssError("Merge policy 'ranked' requires score_key or score_rule.", line=line, column=column)
    if policy == POLICY_RANKED and score_key and score_rule:
        raise Namel3ssError("Merge policy 'ranked' may not set both score_key and score_rule.", line=line, column=column)
    validator = MergeValidator(
        require_keys=list(getattr(merge_policy, "require_keys", None) or []),
        require_non_empty=bool(getattr(merge_policy, "require_non_empty", False)),
    )
    evaluations: list[MergeCandidateEvaluation] = []
    for candidate in candidates:
        valid, reasons = validate_candidate(candidate.output, validator)
        score: Decimal | None = None
        consensus_value: str | None = None
        if policy == POLICY_RANKED:
            if score_rule:
                score, reason = _score_rule_candidate(candidate.output, score_rule)
            else:
                score, reason = _score_candidate(candidate.output, score_key)
            if score is None:
                valid = False
                if reason:
                    reasons.append(reason)
        if policy == POLICY_CONSENSUS:
            consensus_value, reason = _consensus_value(candidate.output, getattr(merge_policy, "consensus_key", None))
            if consensus_value is None:
                valid = False
                if reason:
                    reasons.append(reason)
        evaluations.append(
            MergeCandidateEvaluation(
                agent_name=candidate.agent_name,
                output=candidate.output,
                valid=valid,
                reasons=reasons,
                score=score,
                consensus_value=consensus_value,
            )
        )
    if policy == POLICY_ALL:
        selected = list(range(len(candidates)))
        output = [candidate.output for candidate in candidates]
        return MergeOutcome(policy=policy, output=output, selected=selected, evaluations=evaluations)
    if policy == POLICY_FIRST_VALID:
        for idx, evaluation in enumerate(evaluations):
            if evaluation.valid:
                return MergeOutcome(
                    policy=policy,
                    output=candidates[idx].output,
                    selected=[idx],
                    evaluations=evaluations,
                )
        raise Namel3ssError("No candidates passed validation for merge policy 'first_valid'.", line=line, column=column)
    if policy == POLICY_RANKED:
        scored = [
            (idx, evaluation.score)
            for idx, evaluation in enumerate(evaluations)
            if evaluation.valid and evaluation.score is not None
        ]
        if not scored:
            raise Namel3ssError("No candidates produced a numeric score for merge policy 'ranked'.", line=line, column=column)
        best_idx, _score = max(scored, key=lambda item: (item[1], -item[0]))
        return MergeOutcome(
            policy=policy,
            output=candidates[best_idx].output,
            selected=[best_idx],
            evaluations=evaluations,
        )
    if policy == POLICY_CONSENSUS:
        min_consensus = getattr(merge_policy, "min_consensus", None)
        if not isinstance(min_consensus, int) or min_consensus <= 0:
            raise Namel3ssError("Merge policy 'consensus' requires min_consensus.", line=line, column=column)
        if min_consensus > len(candidates):
            raise Namel3ssError("Consensus threshold exceeds candidate count.", line=line, column=column)
        counts: dict[str, int] = {}
        order: list[str] = []
        for evaluation in evaluations:
            if not evaluation.valid or evaluation.consensus_value is None:
                continue
            value = evaluation.consensus_value
            counts[value] = counts.get(value, 0) + 1
            if value not in order:
                order.append(value)
        winner = _consensus_winner(counts, order, min_consensus)
        if winner is None:
            raise Namel3ssError("No consensus reached for merge policy 'consensus'.", line=line, column=column)
        for idx, evaluation in enumerate(evaluations):
            if evaluation.consensus_value == winner:
                return MergeOutcome(
                    policy=policy,
                    output=candidates[idx].output,
                    selected=[idx],
                    evaluations=evaluations,
                )
        raise Namel3ssError("Consensus winner could not be resolved.", line=line, column=column)
    raise Namel3ssError("Merge policy not supported.", line=line, column=column)


def _score_candidate(output: object, score_key: str | None) -> tuple[Decimal | None, str | None]:
    if not score_key:
        return None, "Score key is required."
    if not isinstance(output, dict):
        return None, "Score key requires map output."
    if score_key not in output:
        return None, f"Missing score key '{score_key}'."
    value = output.get(score_key)
    if not is_number(value):
        return None, f"Score key '{score_key}' must be numeric."
    return to_decimal(value), None


def _score_rule_candidate(output: object, score_rule: str) -> tuple[Decimal | None, str | None]:
    if score_rule != "text_length":
        return None, f"Score rule '{score_rule}' is not supported."
    text = None
    if isinstance(output, dict):
        text = output.get("text")
    elif isinstance(output, str):
        text = output
    if not isinstance(text, str):
        return None, "Score rule requires text output."
    return to_decimal(len(text)), None


def _consensus_value(output: object, consensus_key: str | None) -> tuple[str | None, str | None]:
    if consensus_key:
        if not isinstance(output, dict):
            return None, f"Consensus key '{consensus_key}' requires map output."
        if consensus_key not in output:
            return None, f"Missing consensus key '{consensus_key}'."
        value = output.get(consensus_key)
    else:
        if isinstance(output, dict) and "text" in output:
            value = output.get("text")
        else:
            value = output
    if value is None:
        return None, "Consensus value is empty."
    return _canonical_value(value), None


def _canonical_value(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError:
        return json.dumps(str(value), sort_keys=True, separators=(",", ":"), default=str)


def _consensus_winner(counts: dict[str, int], order: list[str], min_consensus: int) -> str | None:
    winner = None
    best_count = 0
    for value in order:
        count = counts.get(value, 0)
        if count < min_consensus:
            continue
        if count > best_count:
            best_count = count
            winner = value
    return winner


__all__ = [
    "POLICY_ALL",
    "POLICY_CONSENSUS",
    "POLICY_FIRST_VALID",
    "POLICY_RANKED",
    "MergeCandidate",
    "MergeCandidateEvaluation",
    "MergeOutcome",
    "merge_agent_candidates",
]
