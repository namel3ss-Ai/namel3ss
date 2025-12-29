from __future__ import annotations

from namel3ss.runtime.execution.normalize import SKIP_KINDS
from namel3ss.runtime.tools.explain.decision import ToolDecision

from .model import ErrorState


def link_error_to_artifacts(error: ErrorState, packs: dict) -> list[str]:
    lines: list[str] = []
    flow_pack = packs.get("flow")
    if isinstance(flow_pack, dict):
        what_not = flow_pack.get("what_not") or []
        for entry in what_not:
            lines.append(str(entry))

    execution = packs.get("execution")
    if isinstance(execution, dict):
        steps = execution.get("execution_steps") or []
        for step in steps:
            if not isinstance(step, dict):
                continue
            if step.get("kind") not in SKIP_KINDS:
                continue
            lines.append(_step_line(step))

    tools = packs.get("tools")
    if isinstance(tools, dict):
        decisions = _decisions(tools)
        for decision in decisions:
            if decision.status == "blocked":
                lines.append(_blocked_tool_line(decision))
            elif decision.status == "error":
                lines.append(_error_tool_line(decision))

    ui = packs.get("ui")
    if isinstance(ui, dict):
        actions = ui.get("actions") or []
        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("status") != "not available":
                continue
            requires = action.get("requires")
            if requires:
                lines.append(f"Action {action.get('id')} not available because requires {requires}.")
            else:
                lines.append(f"Action {action.get('id')} not available.")

    return _dedupe(lines, limit=8)


def _step_line(step: dict) -> str:
    what = str(step.get("what") or "").strip()
    because = step.get("because")
    if not what:
        return ""
    if because:
        return f"{_strip_period(what)} because {because}."
    return _ensure_period(what)


def _blocked_tool_line(decision: ToolDecision) -> str:
    reason = decision.permission.reasons[0] if decision.permission.reasons else None
    if reason:
        return f'tool "{decision.tool_name}" was blocked because {reason}.'
    return f'tool "{decision.tool_name}" was blocked.'


def _error_tool_line(decision: ToolDecision) -> str:
    message = decision.effect.error_message or decision.effect.error_type
    if message:
        return f'tool "{decision.tool_name}" failed: {message}.'
    return f'tool "{decision.tool_name}" failed.'


def _decisions(tools: dict) -> list[ToolDecision]:
    decisions = tools.get("decisions") or []
    parsed: list[ToolDecision] = []
    for entry in decisions:
        if isinstance(entry, dict):
            parsed.append(ToolDecision.from_dict(entry))
    return parsed


def _strip_period(text: str) -> str:
    return text[:-1] if text.endswith(".") else text


def _ensure_period(text: str) -> str:
    return text if text.endswith(".") else f"{text}."


def _dedupe(lines: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        text = line.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


__all__ = ["link_error_to_artifacts"]
