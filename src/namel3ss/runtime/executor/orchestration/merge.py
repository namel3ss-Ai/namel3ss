from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class OrchestrationBranchResult:
    name: str
    status: str
    value: object | None
    error_type: str | None
    error_message: str | None


@dataclass(frozen=True)
class OrchestrationMergeOutcome:
    policy: str
    status: str
    output: object | None
    selected: str | None
    reason: str
    failed: list[str]
    precedence: list[str] | None
    branches: list[OrchestrationBranchResult]


def merge_branch_results(
    *,
    policy: str,
    branches: list[OrchestrationBranchResult],
    precedence: list[str] | None,
) -> tuple[OrchestrationMergeOutcome, str | None]:
    if policy not in {"first_ok", "all_ok", "collect", "prefer", "strict"}:
        raise Namel3ssError(f"Unknown orchestration merge policy '{policy}'.")
    failed = [branch.name for branch in branches if branch.status != "ok"]
    branch_order = [branch.name for branch in branches]
    if policy == "collect":
        outcome = OrchestrationMergeOutcome(
            policy=policy,
            status="ok",
            output=[
                _collect_entry(branch)
                for branch in branches
            ],
            selected=None,
            reason="Collected branch outcomes.",
            failed=list(failed),
            precedence=precedence,
            branches=list(branches),
        )
        return outcome, None
    if policy in {"all_ok", "strict"}:
        if failed:
            reason = f"Merge failed because branches failed: {', '.join(failed)}."
            outcome = OrchestrationMergeOutcome(
                policy=policy,
                status="error",
                output=None,
                selected=None,
                reason=reason,
                failed=list(failed),
                precedence=precedence,
                branches=list(branches),
            )
            message = _merge_failure_message(policy, failed)
            return outcome, message
        output: object
        if policy == "all_ok":
            output = [branch.value for branch in branches]
        else:
            output = {branch.name: branch.value for branch in branches}
        outcome = OrchestrationMergeOutcome(
            policy=policy,
            status="ok",
            output=output,
            selected=None,
            reason="All branches succeeded.",
            failed=[],
            precedence=precedence,
            branches=list(branches),
        )
        return outcome, None
    if policy == "first_ok":
        selected = _select_first_ok(branches)
        if selected is None:
            outcome = OrchestrationMergeOutcome(
                policy=policy,
                status="error",
                output=None,
                selected=None,
                reason="Merge failed because no branch succeeded.",
                failed=list(failed),
                precedence=precedence,
                branches=list(branches),
            )
            return outcome, "Orchestration merge failed: first_ok requires at least one successful branch."
        outcome = OrchestrationMergeOutcome(
            policy=policy,
            status="ok",
            output=selected.value,
            selected=selected.name,
            reason=f'Selected "{selected.name}" because it was first in branch order.',
            failed=list(failed),
            precedence=precedence,
            branches=list(branches),
        )
        return outcome, None
    if policy == "prefer":
        order = _precedence_order(branch_order, precedence)
        selected = _select_first_ok([_branch_by_name(branches, name) for name in order])
        if selected is None:
            outcome = OrchestrationMergeOutcome(
                policy=policy,
                status="error",
                output=None,
                selected=None,
                reason="Merge failed because no preferred branch succeeded.",
                failed=list(failed),
                precedence=list(order),
                branches=list(branches),
            )
            return outcome, "Orchestration merge failed: prefer requires at least one successful branch."
        outcome = OrchestrationMergeOutcome(
            policy=policy,
            status="ok",
            output=selected.value,
            selected=selected.name,
            reason=f'Selected "{selected.name}" due to precedence.',
            failed=list(failed),
            precedence=list(order),
            branches=list(branches),
        )
        return outcome, None
    raise Namel3ssError(f"Unknown orchestration merge policy '{policy}'.")


def _select_first_ok(branches: list[OrchestrationBranchResult]) -> OrchestrationBranchResult | None:
    for branch in branches:
        if branch.status == "ok":
            return branch
    return None


def _merge_failure_message(policy: str, failed: list[str]) -> str:
    failed_text = ", ".join(failed)
    return f"Orchestration merge failed: {policy} requires all branches to succeed. Failed branches: {failed_text}."


def _branch_by_name(branches: list[OrchestrationBranchResult], name: str) -> OrchestrationBranchResult:
    for branch in branches:
        if branch.name == name:
            return branch
    raise Namel3ssError(f"Unknown orchestration branch '{name}'.")


def _precedence_order(branch_order: list[str], precedence: list[str] | None) -> list[str]:
    if not precedence:
        return list(branch_order)
    remaining = [name for name in branch_order if name not in precedence]
    return list(precedence) + remaining


def _collect_entry(branch: OrchestrationBranchResult) -> dict:
    entry = {"branch": branch.name, "status": branch.status}
    if branch.status == "ok":
        entry["value"] = branch.value
    else:
        entry["error_type"] = branch.error_type or "Error"
        entry["error_message"] = branch.error_message or "Unknown error."
    return entry


__all__ = [
    "OrchestrationBranchResult",
    "OrchestrationMergeOutcome",
    "merge_branch_results",
]
