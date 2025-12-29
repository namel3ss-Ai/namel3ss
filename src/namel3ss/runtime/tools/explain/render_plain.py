from __future__ import annotations

from .decision import ToolDecision
from .normalize import stable_bullets, stable_truncate


def render_with(decisions: list[ToolDecision]) -> str:
    if not decisions:
        return "No tools were used in the last run."
    lines: list[str] = []
    lines.append("Tools used in the last run")
    lines.append("")
    for decision in decisions:
        lines.extend(_render_decision(decision))
        lines.append("")
    blocked = [d for d in decisions if d.status == "blocked"]
    if blocked:
        lines.append("Blocked tools")
        lines.extend(stable_bullets([_blocked_line(d) for d in blocked]))
    return "\n".join(lines).rstrip()


def _render_decision(decision: ToolDecision) -> list[str]:
    lines: list[str] = []
    lines.append(f"- {decision.tool_name}")
    intent = decision.intent.what if decision.intent else None
    if intent:
        lines.append(f"  - intent: {stable_truncate(intent)}")
    lines.append(f"  - { _permission_label(decision) }")
    runner = decision.details.get("runner")
    if runner:
        lines.append(f"  - runner: {runner}")
    lines.append(f"  - result: {decision.status}")
    if decision.status == "blocked":
        reason = _first_reason(decision)
        lines.append(f"  - why: {stable_truncate(reason)}")
    elif decision.status == "error":
        error_message = decision.effect.error_message
        if error_message:
            lines.append(f"  - error: {stable_truncate(error_message)}")
    return lines


def _permission_label(decision: ToolDecision) -> str:
    allowed = decision.permission.allowed
    if allowed is True:
        return "allowed"
    if allowed is False:
        return "blocked"
    return "permission: unknown"


def _blocked_line(decision: ToolDecision) -> str:
    reason = _first_reason(decision)
    return stable_truncate(f"{decision.tool_name}: {reason}")


def _first_reason(decision: ToolDecision) -> str:
    reasons = decision.permission.reasons or []
    if reasons:
        return str(reasons[0])
    return "No explicit reason recorded."


__all__ = ["render_with"]
