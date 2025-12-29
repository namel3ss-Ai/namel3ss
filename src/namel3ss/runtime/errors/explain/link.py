from __future__ import annotations

from namel3ss.runtime.execution.normalize import SKIP_KINDS
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
        entries = _tool_entries(tools)
        for entry in entries:
            if entry.get("result") == "blocked":
                lines.append(_blocked_tool_line(entry))
            elif entry.get("result") == "error":
                lines.append(_error_tool_line(entry))

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


def _blocked_tool_line(entry: dict) -> str:
    reason = entry.get("reason")
    tool_name = entry.get("tool") or "tool"
    if reason and reason != "unknown":
        return f'tool "{tool_name}" was blocked because {reason}.'
    return f'tool "{tool_name}" was blocked.'


def _error_tool_line(entry: dict) -> str:
    tool_name = entry.get("tool") or "tool"
    message = entry.get("error_message") or entry.get("error_type")
    if message:
        return f'tool "{tool_name}" failed: {message}.'
    return f'tool "{tool_name}" failed.'


def _tool_entries(tools: dict) -> list[dict]:
    if any(key in tools for key in ("allowed", "blocked", "errors")):
        entries: list[dict] = []
        for key in ("allowed", "blocked", "errors"):
            values = tools.get(key) or []
            if isinstance(values, list):
                entries.extend([item for item in values if isinstance(item, dict)])
        return entries
    decisions = tools.get("decisions") or []
    if not isinstance(decisions, list):
        return []
    entries: list[dict] = []
    for entry in decisions:
        if isinstance(entry, dict):
            entries.append(_entry_from_decision(entry))
    return entries


def _entry_from_decision(entry: dict) -> dict:
    tool_name = str(entry.get("tool_name") or "tool")
    status = str(entry.get("status") or "")
    permission = entry.get("permission") if isinstance(entry.get("permission"), dict) else {}
    reasons = permission.get("reasons") if isinstance(permission.get("reasons"), list) else []
    capabilities = permission.get("capabilities_used") if isinstance(permission.get("capabilities_used"), list) else []
    effect = entry.get("effect") if isinstance(entry.get("effect"), dict) else {}
    reason = str(reasons[0]) if reasons else "unknown"
    capability = str(capabilities[0]) if capabilities else "none"
    result = status if status in {"ok", "blocked", "error"} else "ok"
    return {
        "tool": tool_name,
        "decision": "blocked" if result == "blocked" else "allowed",
        "capability": capability,
        "reason": reason,
        "result": result,
        "error_message": effect.get("error_message"),
        "error_type": effect.get("error_type"),
    }


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
