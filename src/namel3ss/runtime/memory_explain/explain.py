from __future__ import annotations

from typing import Mapping

from namel3ss.runtime.memory_explain.model import Explanation
from namel3ss.runtime.memory_explain.ordering import (
    order_counts,
    order_phase_counts,
    order_recall_reasons,
    order_spaces,
)
from namel3ss.runtime.memory_explain.templates import (
    conflict_rule_line,
    deleted_reason_line,
    denied_fix_line,
    denied_reason_line,
    forget_reason_line,
    recall_reason_line,
    rule_action_line,
    rule_reason_line,
)
from namel3ss.traces.builders import build_memory_explanation


def explain_trace_event(event: Mapping[str, object], context: Mapping[str, object] | None = None) -> Explanation | None:
    event_type = event.get("type")
    if event_type == "memory_recall":
        return explain_memory_recall(event)
    if event_type == "memory_denied":
        return explain_memory_denied(event)
    if event_type == "memory_deleted":
        return explain_memory_deleted(event)
    if event_type == "memory_forget":
        return explain_memory_forget(event)
    if event_type == "memory_conflict":
        return explain_memory_conflict(event)
    if event_type == "memory_phase_diff":
        return explain_memory_phase_diff(event)
    if event_type == "memory_rule_applied":
        return explain_memory_rule_applied(event)
    return None


def append_explanation_events(events: list[dict]) -> list[dict]:
    explained: list[dict] = []
    for event in events:
        index = len(explained)
        explained.append(event)
        explanation = explain_trace_event(event)
        if explanation is None:
            continue
        explained.append(
            build_memory_explanation(
                for_event_index=index,
                title=explanation.title,
                lines=explanation.lines,
                related_ids=explanation.related_ids,
            )
        )
    return explained


def explain_memory_recall(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = []
    current_phase = _as_dict(event.get("current_phase"))
    phase_id = current_phase.get("phase_id") or "unknown"
    lines.append(f"Phase used is {phase_id}.")

    spaces = _as_list(event.get("spaces_consulted"))
    if spaces:
        ordered = order_spaces([str(space) for space in spaces])
        lines.append(f"Spaces checked are {', '.join(ordered)}.")

    recalled = _as_list(event.get("recalled"))
    lines.append(f"Recalled items count is {len(recalled)}.")

    policy = _as_dict(event.get("policy"))
    phase_mode = policy.get("phase_mode")
    if phase_mode == "current_only":
        lines.append("Only the current phase was used.")
        lines.append("Older phases were ignored.")
    elif phase_mode == "current_plus_history":
        lines.append("Current and older phases were used.")

    recall_counts = _as_dict(event.get("recall_counts"))
    for space, count in order_counts(_int_map(recall_counts)):
        if count == 0:
            lines.append(f"No items were recalled from {space}.")
        else:
            lines.append(f"Items recalled from {space} count is {count}.")

    phase_counts = _map_of_ints(event.get("phase_counts"))
    for space in order_spaces(list(phase_counts.keys())):
        counts = phase_counts.get(space, {})
        for phase, count in order_phase_counts(counts):
            lines.append(f"Phase {phase} count in {space} is {count}.")

    reasons = _collect_recall_reasons(recalled)
    for reason in order_recall_reasons(reasons):
        line = recall_reason_line(reason)
        if line:
            lines.append(f"Recall reason is {line}.")
        else:
            lines.append(f"Recall reason is {reason}.")

    return Explanation(title="Memory recall", lines=lines)


def explain_memory_denied(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = ["Write was blocked."]
    attempted = _as_dict(event.get("attempted"))
    kind = attempted.get("kind")
    if kind:
        lines.append(f"Blocked kind is {kind}.")
    event_type = _as_dict(attempted.get("meta")).get("event_type")
    if event_type:
        lines.append(f"Blocked event type is {event_type}.")
    reason = str(event.get("reason") or "unknown")
    reason_line = denied_reason_line(reason)
    if reason_line:
        lines.append(reason_line)
    else:
        lines.append("Policy blocked this write.")
    fix_line = denied_fix_line(reason)
    if fix_line:
        lines.append(fix_line)
    return Explanation(title="Memory denied", lines=lines)


def explain_memory_deleted(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = []
    memory_id = event.get("memory_id") or "unknown"
    lines.append(f"Deleted id is {memory_id}.")
    reason = str(event.get("reason") or "unknown")
    reason_line = deleted_reason_line(_normalize_delete_reason(reason))
    if reason_line:
        lines.append(reason_line)
    else:
        lines.append(f"Reason is {reason}.")
    replaced_by = event.get("replaced_by")
    if replaced_by:
        lines.append(f"Replaced by id is {replaced_by}.")
    return Explanation(title="Memory deleted", lines=lines, related_ids=_related_ids(memory_id, replaced_by))


def explain_memory_forget(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = []
    memory_id = event.get("memory_id") or "unknown"
    lines.append(f"Forgotten id is {memory_id}.")
    reason = str(event.get("reason") or "unknown")
    reason_line = forget_reason_line(reason)
    if reason_line:
        lines.append(reason_line)
    else:
        lines.append(f"Reason is {reason}.")
    return Explanation(title="Memory forgotten", lines=lines, related_ids=_related_ids(memory_id))


def explain_memory_conflict(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = ["Conflict detected."]
    winner_id = event.get("winner_id") or "unknown"
    loser_id = event.get("loser_id") or "unknown"
    lines.append(f"Winner id is {winner_id}.")
    lines.append(f"Loser id is {loser_id}.")
    rule = str(event.get("rule") or "unknown")
    rule_line = conflict_rule_line(rule)
    if rule_line:
        lines.append(rule_line)
    else:
        lines.append(f"Winner rule is {rule}.")
    return Explanation(title="Memory conflict", lines=lines, related_ids=_related_ids(winner_id, loser_id))


def explain_memory_phase_diff(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = []
    from_phase = event.get("from_phase_id") or "unknown"
    to_phase = event.get("to_phase_id") or "unknown"
    lines.append(f"Phase diff from {from_phase} to {to_phase}.")
    lines.append(f"Added count is {int(event.get('added_count') or 0)}.")
    lines.append(f"Deleted count is {int(event.get('deleted_count') or 0)}.")
    lines.append(f"Replaced count is {int(event.get('replaced_count') or 0)}.")

    changes = _as_list(event.get("top_changes"))
    for change in changes[:6]:
        if not isinstance(change, dict):
            continue
        change_type = change.get("change")
        if change_type == "added":
            memory_id = change.get("memory_id") or "unknown"
            kind = change.get("kind") or "unknown"
            lines.append(f"Added {memory_id} kind {kind}.")
        elif change_type == "deleted":
            memory_id = change.get("memory_id") or "unknown"
            kind = change.get("kind") or "unknown"
            lines.append(f"Deleted {memory_id} kind {kind}.")
        elif change_type == "replaced":
            from_id = change.get("from_id") or "unknown"
            to_id = change.get("to_id") or "unknown"
            lines.append(f"Replaced {from_id} with {to_id}.")
    return Explanation(title="Memory phase diff", lines=lines)


def explain_memory_rule_applied(event: Mapping[str, object]) -> Explanation:
    lines: list[str] = []
    rule_text = event.get("rule_text")
    if rule_text:
        lines.append(f"Rule text is {rule_text}.")
    action = event.get("action")
    if action:
        action_line = rule_action_line(str(action))
        if action_line:
            lines.append(f"Action is {action_line}.")
        else:
            lines.append(f"Action is {action}.")
    allowed = event.get("allowed")
    if allowed is True:
        lines.append("Allowed is yes.")
    elif allowed is False:
        lines.append("Allowed is no.")
    reason = event.get("reason")
    if reason:
        reason_line = rule_reason_line(str(reason))
        if reason_line:
            lines.append(reason_line)
        else:
            lines.append(f"Reason is {reason}.")
    return Explanation(title="Memory rule applied", lines=lines)


def _collect_recall_reasons(recalled: list[object]) -> list[str]:
    reasons: list[str] = []
    for item in recalled:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta") or {}
        recall_reason = meta.get("recall_reason") or []
        if not isinstance(recall_reason, list):
            continue
        for reason in recall_reason:
            if not isinstance(reason, str):
                continue
            if reason.startswith("space:") or reason.startswith("phase:"):
                continue
            if reason not in reasons:
                reasons.append(reason)
    return reasons


def _related_ids(*values: object) -> list[str] | None:
    related = [str(value) for value in values if value]
    return related or None


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _int_map(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, int] = {}
    for key, item in value.items():
        try:
            output[str(key)] = int(item)
        except (TypeError, ValueError):
            output[str(key)] = 0
    return output


def _map_of_ints(value: object) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, dict[str, int]] = {}
    for key, item in value.items():
        output[str(key)] = _int_map(item)
    return output


def _normalize_delete_reason(reason: str) -> str:
    if reason == "superseded":
        return "replaced"
    return reason


__all__ = [
    "append_explanation_events",
    "explain_memory_conflict",
    "explain_memory_deleted",
    "explain_memory_denied",
    "explain_memory_forget",
    "explain_memory_phase_diff",
    "explain_memory_rule_applied",
    "explain_memory_recall",
    "explain_trace_event",
]
