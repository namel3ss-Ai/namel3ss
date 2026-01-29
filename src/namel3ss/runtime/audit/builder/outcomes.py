from __future__ import annotations

from namel3ss.ingestion.policy import PolicyDecision


def build_outcomes(
    state: dict,
    policy_decisions: dict[str, PolicyDecision],
    retrieval_outcome: dict | None,
    upload_id: str | None,
) -> dict:
    ingestion = state.get("ingestion")
    status_counts = {"pass": 0, "warn": 0, "block": 0}
    upload_status = None
    if isinstance(ingestion, dict):
        for uid, report in ingestion.items():
            if not isinstance(report, dict):
                continue
            status = report.get("status")
            if status in status_counts:
                status_counts[status] += 1
            if upload_id and str(uid) == upload_id:
                upload_status = status
    policy_denied = [
        action for action, decision in policy_decisions.items() if not decision.allowed
    ]
    outcomes: dict[str, object] = {
        "ingestion": {"counts": status_counts},
        "policy_denials": sorted(policy_denied),
    }
    if upload_status is not None:
        outcomes["ingestion"]["upload_status"] = upload_status
    if retrieval_outcome is not None:
        outcomes["retrieval"] = {
            "results": len(retrieval_outcome.get("results") or []),
            "preferred_quality": retrieval_outcome.get("preferred_quality"),
            "included_warn": retrieval_outcome.get("included_warn"),
            "excluded_blocked": retrieval_outcome.get("excluded_blocked"),
            "excluded_warn": retrieval_outcome.get("excluded_warn"),
        }
    return outcomes


__all__ = ["build_outcomes"]
