from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.errors.explain.model import ErrorState, ErrorWhere
from namel3ss.runtime.tools.explain.decision import ToolDecision


def collect_last_error(project_root: Path) -> ErrorState | None:
    run_last = _load_json(project_root / ".namel3ss" / "run" / "last.json")
    if not isinstance(run_last, dict):
        return None
    if bool(run_last.get("ok", True)):
        return None

    flow_name = run_last.get("flow_name")
    error_type = run_last.get("error_type") or run_last.get("error", {}).get("kind")
    error_message = run_last.get("error_message") or run_last.get("error", {}).get("message")
    error_step_id = run_last.get("error_step_id") or _error_step_id(project_root)

    tools_last = _load_json(project_root / ".namel3ss" / "tools" / "last.json")
    tool_name, tool_kind = _tool_error(tools_last)
    kind = _infer_kind(error_type, error_message, tool_kind)

    what, why = _parse_guidance(error_message)
    if not what:
        what = str(error_message or error_type or "error")
    where = ErrorWhere(flow_name=flow_name, step_id=error_step_id, tool_name=tool_name)
    details = {
        "error_type": error_type,
        "error_message": error_message,
        "error_step_id": error_step_id,
    }
    return ErrorState(
        id="error:1",
        kind=kind,
        where=where,
        what=what,
        why=why,
        details=details,
        impact=[],
        recoverable=False,
        recovery_options=[],
    )


def _tool_error(tools_last: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(tools_last, dict):
        return None, None
    decisions = tools_last.get("decisions") or []
    parsed: list[ToolDecision] = []
    for entry in decisions:
        if isinstance(entry, dict):
            parsed.append(ToolDecision.from_dict(entry))
    for decision in parsed:
        if decision.status == "blocked":
            return decision.tool_name, "permission"
    for decision in parsed:
        if decision.status == "error":
            return decision.tool_name, "tool"
    return None, None


def _infer_kind(error_type: str | None, error_message: str | None, tool_kind: str | None) -> str:
    if tool_kind:
        return tool_kind
    if error_type == "CapabilityViolation":
        return "permission"
    if _message_mentions_identity(error_message):
        return "permission"
    if error_type == "Namel3ssError":
        return "validation"
    if error_message and "memory" in error_message.lower():
        return "memory"
    return "execution" if error_type else "unknown"


def _message_mentions_identity(error_message: str | None) -> bool:
    if not error_message:
        return False
    lowered = error_message.lower()
    return "identity" in lowered or "requires" in lowered


def _error_step_id(project_root: Path) -> str | None:
    execution = _load_json(project_root / ".namel3ss" / "execution" / "last.json")
    if not isinstance(execution, dict):
        return None
    steps = execution.get("execution_steps") or []
    if not isinstance(steps, list):
        return None
    for step in reversed(steps):
        if isinstance(step, dict) and step.get("kind") == "error" and step.get("id"):
            return str(step.get("id"))
    return None


def _parse_guidance(message: str | None) -> tuple[str | None, str | None]:
    if not message:
        return None, None
    what = None
    why = None
    for line in str(message).splitlines():
        line = line.strip()
        if line.startswith("What happened:"):
            what = line.replace("What happened:", "").strip()
        elif line.startswith("Why:"):
            why = line.replace("Why:", "").strip()
    return what, why


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = ["collect_last_error"]
