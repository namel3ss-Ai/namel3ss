from __future__ import annotations

from pathlib import Path

from namel3ss.ingestion.policy import ACTION_RETRIEVAL_INCLUDE_WARN, PolicyDecision
from namel3ss.retrieval.api import run_retrieval

from .model import DecisionStep


_RETRIEVAL_RULES = [
    "blocked uploads are excluded",
    "pass results are preferred",
    "warn results require policy allow",
]


def build_retrieval_step(
    state: dict,
    policy_decision: PolicyDecision | None,
    policy_rule: dict | None,
    *,
    query: str | None,
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: list[str] | None,
) -> tuple[DecisionStep | None, dict | None]:
    if query is None:
        return None, None
    policy_value = policy_decision
    if policy_value is None:
        policy_value = PolicyDecision(
            action=ACTION_RETRIEVAL_INCLUDE_WARN,
            allowed=False,
            reason="policy_missing",
            required_permissions=(),
            source="default",
        )
    result = run_retrieval(
        query=query,
        state=state,
        project_root=str(project_root) if project_root else None,
        app_path=str(app_path) if app_path else None,
        secret_values=secret_values,
        policy_decision=policy_value,
    )
    proof = _retrieval_proof(state, result, policy_value)
    rules = list(_RETRIEVAL_RULES)
    if policy_rule:
        rules.append({"warn_policy": policy_rule})
    outcome = {
        "query": result.get("query"),
        "preferred_quality": result.get("preferred_quality"),
        "included_warn": result.get("included_warn"),
        "excluded_blocked": result.get("excluded_blocked"),
        "excluded_warn": result.get("excluded_warn"),
        "warn_policy": _policy_summary(policy_value),
        "results": _retrieval_results(result),
        "decisions": proof,
    }
    step = DecisionStep(
        id="retrieval:query",
        category="retrieval",
        subject=result.get("query"),
        inputs={"query": result.get("query")},
        rules=rules,
        outcome=outcome,
    )
    return step, outcome


def _retrieval_results(result: dict) -> list[dict]:
    items = result.get("results") if isinstance(result, dict) else None
    if not isinstance(items, list):
        return []
    normalized: list[dict] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "upload_id": entry.get("upload_id"),
                "chunk_id": entry.get("chunk_id"),
                "quality": entry.get("quality"),
            }
        )
    return normalized


def _retrieval_proof(
    state: dict,
    result: dict,
    policy_decision: PolicyDecision,
) -> list[dict]:
    query_text = str(result.get("query") or "")
    status_map = _ingestion_status_map(state)
    candidates = _retrieval_candidates(state, query_text)
    pass_matches = {
        uid
        for uid, entries in candidates.items()
        if _quality_for_upload(status_map, uid) == "pass" and entries
    }
    has_pass = bool(pass_matches)
    warn_allowed = bool(policy_decision.allowed)
    decisions: list[dict] = []
    for uid in sorted(status_map.keys(), key=lambda item: str(item)):
        report = status_map.get(uid) or {}
        quality = _quality_for_upload(status_map, uid)
        reasons = _string_list(report.get("reasons"))
        matched = bool(candidates.get(uid))
        decision, reason = _retrieval_decision_for(quality, matched, has_pass, warn_allowed)
        decisions.append(
            {
                "upload_id": uid,
                "quality": quality,
                "matched": matched,
                "decision": decision,
                "reason": reason,
                "reasons": reasons,
            }
        )
    ordered = sorted(decisions, key=_retrieval_decision_key)
    return ordered


def _retrieval_decision_for(
    quality: str, matched: bool, has_pass: bool, warn_allowed: bool
) -> tuple[str, str]:
    if quality == "block":
        return "exclude", "blocked"
    if quality == "pass":
        if matched:
            return "include", "matched"
        return "exclude", "no_match"
    if not matched:
        return "exclude", "no_match"
    if has_pass:
        return "exclude", "pass_preferred"
    if not warn_allowed:
        return "exclude", "policy_denied"
    return "include", "warn_allowed"


def _retrieval_decision_key(entry: dict) -> tuple[int, str]:
    quality = entry.get("quality")
    order = {"block": 0, "warn": 1, "pass": 2}.get(quality, 9)
    upload_id = str(entry.get("upload_id") or "")
    return (order, upload_id)


def _retrieval_candidates(state: dict, query_text: str) -> dict[str, list[dict]]:
    candidates: dict[str, list[dict]] = {}
    index = state.get("index")
    chunks = index.get("chunks") if isinstance(index, dict) else None
    if not isinstance(chunks, list):
        return candidates
    for entry in chunks:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        text_value = text if isinstance(text, str) else ""
        if query_text and query_text not in text_value.lower():
            continue
        upload_value = entry.get("upload_id")
        upload_id = str(upload_value) if upload_value is not None else ""
        if not upload_id:
            continue
        candidates.setdefault(upload_id, []).append(entry)
    return candidates


def _ingestion_status_map(state: dict) -> dict[str, dict]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {}
    return {str(key): value for key, value in ingestion.items() if isinstance(value, dict)}


def _quality_for_upload(status_map: dict[str, dict], upload_id: str) -> str:
    report = status_map.get(upload_id)
    if not isinstance(report, dict):
        return "block"
    status = report.get("status")
    if status in {"pass", "warn", "block"}:
        return str(status)
    return "block"


def _policy_summary(decision: PolicyDecision) -> dict:
    return {
        "action": decision.action,
        "decision": "allowed" if decision.allowed else "denied",
        "reason": decision.reason,
        "required_permissions": list(decision.required_permissions),
        "source": decision.source,
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


__all__ = ["build_retrieval_step"]
