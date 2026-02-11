from __future__ import annotations

from collections.abc import Mapping

from namel3ss.retrieval.tuning import RETRIEVAL_TUNING_FLOWS

_UNSUPPORTED_ACTION_TYPES = {
    "retrieval_run",
    "ingestion_review",
    "ingestion_skip",
    "upload_replace",
}


def filter_export_actions(actions: Mapping[str, object]) -> tuple[dict[str, dict], list[dict[str, str]]]:
    filtered: dict[str, dict] = {}
    skipped: list[dict[str, str]] = []
    for action_id in sorted(actions.keys()):
        entry = actions.get(action_id)
        action = dict(entry) if isinstance(entry, Mapping) else {}
        skip_reason = _skip_reason(action_id, action)
        if skip_reason:
            skipped.append({"id": action_id, "reason": skip_reason})
            continue
        filtered[action_id] = action
    return filtered, skipped


def _skip_reason(action_id: str, action: dict[str, object]) -> str | None:
    if bool(action.get("debug_only")):
        return "debug_only"
    action_type = str(action.get("type") or "")
    if action_type in _UNSUPPORTED_ACTION_TYPES:
        return f"unsupported_type:{action_type}"
    if action_type == "call_flow":
        flow_name = str(action.get("flow") or "")
        if flow_name in set(RETRIEVAL_TUNING_FLOWS) and action.get("system_action") == "retrieval_tuning":
            return "studio_only_retrieval_tuning"
    if action.get("export_supported") is False:
        return "explicitly_unsupported"
    if not action_id:
        return "missing_id"
    return None


__all__ = ["filter_export_actions"]
