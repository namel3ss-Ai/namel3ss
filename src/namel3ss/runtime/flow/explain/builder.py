from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.execution.normalize import SKIP_KINDS, format_expression, summarize_value
from .effects import (
    expected_effects_from_memory,
    expected_effects_from_steps,
    expected_effects_from_tools,
    memory_write_count,
    summarize_memory,
    summarize_tool_decisions,
    unique_items,
)
from .model import FlowIntent, FlowOutcome, FlowSummary
from .normalize import build_plain_text, normalize_lines, write_last_flow
from .render_plain import render_what

API_VERSION = "flow.v1"


def build_flow_explain_pack(project_root: Path, app_path: str | None = None) -> dict | None:
    run_last = _load_last_run(project_root)
    execution_last = _load_last_execution(project_root)
    if run_last is None and execution_last is None:
        return None
    tools_last = _load_last_tools(project_root)
    memory_last = _load_last_memory(project_root)

    flow_name = _flow_name(run_last, execution_last)
    steps = _execution_steps(execution_last)
    tool_entries = _tool_entries(tools_last)

    intent = _build_intent(flow_name, app_path, steps, tool_entries, memory_last)
    outcome = _build_outcome(run_last, execution_last, steps, tool_entries, memory_last)
    summary = FlowSummary(
        intent=intent,
        outcome=outcome,
        reasons=_build_reasons(steps, tool_entries, memory_last),
        what_not=_build_what_not(steps, tool_entries, memory_last),
    )

    status = summary.outcome.status
    pack = {
        "ok": status != "error",
        "api_version": API_VERSION,
        "flow_name": flow_name,
        "intent": summary.intent.as_dict(),
        "outcome": summary.outcome.as_dict(),
        "reasons": list(summary.reasons),
        "what_not": list(summary.what_not),
        "summary": _summary_text(flow_name, status),
    }
    return pack


def write_flow_explain_artifacts(root: Path, pack: dict) -> str:
    text = render_what(pack)
    plain = build_plain_text(pack)
    write_last_flow(root, pack, plain, text)
    return text


def _build_intent(
    flow_name: str,
    app_path: str | None,
    steps: list[dict],
    tool_entries: list[dict],
    memory_last: dict | None,
) -> FlowIntent:
    purpose = _purpose_text(flow_name, tool_entries)
    requires, audited = _flow_policy(app_path, flow_name)
    expected: list[str] = []
    expected.extend(expected_effects_from_steps(steps))
    expected.extend(expected_effects_from_tools(tool_entries))
    expected.extend(expected_effects_from_memory(memory_last))
    expected = unique_items(expected)
    return FlowIntent(
        flow_name=flow_name,
        purpose=purpose,
        requires=requires,
        audited=audited,
        expected_effects=expected,
    )


def _build_outcome(
    run_last: dict | None,
    execution_last: dict | None,
    steps: list[dict],
    tool_entries: list[dict],
    memory_last: dict | None,
) -> FlowOutcome:
    tool_summary = summarize_tool_decisions(tool_entries)
    memory_summary = summarize_memory(memory_last)
    skipped_summary = _summarize_skips(steps, tool_summary)
    ok = _run_ok(run_last, execution_last)
    status = _status_from(ok, tool_summary, skipped_summary)
    returned = _has_step_kind(steps, "statement_return")
    return_summary = _return_summary(run_last, returned)
    return FlowOutcome(
        status=status,
        returned=returned,
        return_summary=return_summary,
        tool_summary=tool_summary,
        memory_summary=memory_summary,
        skipped_summary=skipped_summary,
    )


def _build_reasons(steps: list[dict], tool_entries: list[dict], memory_last: dict | None) -> list[str]:
    lines: list[str] = []
    for step in steps:
        if step.get("kind") in {
            "decision_if",
            "decision_match",
            "decision_repeat",
            "decision_for_each",
            "decision_try",
            "branch_taken",
            "case_taken",
            "otherwise_taken",
            "catch_taken",
            "statement_return",
        }:
            line = _step_line(step)
            if line:
                lines.append(line)
    written = memory_write_count(memory_last)
    if written and written > 0:
        lines.append(f"wrote {written} memory items.")
    for entry in tool_entries:
        if entry.get("result") != "blocked":
            continue
        lines.append(_tool_blocked_line(entry, verb="was blocked"))
    return normalize_lines(lines)


def _build_what_not(steps: list[dict], tool_entries: list[dict], memory_last: dict | None) -> list[str]:
    lines: list[str] = []
    for step in steps:
        if step.get("kind") in SKIP_KINDS:
            line = _step_line(step)
            if line:
                lines.append(line)
    for entry in tool_entries:
        if entry.get("result") != "blocked":
            continue
        lines.append(_tool_blocked_line(entry, verb="did not run"))
    lines.extend(_memory_skip_lines(memory_last))
    return normalize_lines(lines)


def _flow_name(run_last: dict | None, execution_last: dict | None) -> str:
    for pack in (run_last, execution_last):
        if isinstance(pack, dict) and pack.get("flow_name"):
            return str(pack.get("flow_name"))
    return "unknown"


def _purpose_text(flow_name: str, tool_entries: list[dict]) -> str:
    tool_name = _primary_tool(tool_entries)
    if tool_name and flow_name != "unknown":
        return f"run flow \"{flow_name}\" to use tool \"{tool_name}\""
    if flow_name != "unknown":
        return f"run flow \"{flow_name}\""
    return "run the flow"


def _flow_policy(app_path: str | None, flow_name: str) -> tuple[str | None, bool]:
    if not app_path or flow_name == "unknown":
        return None, False
    try:
        program, _sources = load_program(app_path)
    except Exception:
        return None, False
    for flow in getattr(program, "flows", []):
        if getattr(flow, "name", None) != flow_name:
            continue
        requires_expr = getattr(flow, "requires", None)
        requires_text = format_expression(requires_expr) if requires_expr else None
        audited = bool(getattr(flow, "audited", False))
        return requires_text, audited
    return None, False


def _execution_steps(execution_last: dict | None) -> list[dict]:
    if not isinstance(execution_last, dict):
        return []
    steps = execution_last.get("execution_steps") or []
    return [step for step in steps if isinstance(step, dict)]


def _tool_entries(tools_last: dict | None) -> list[dict]:
    if not isinstance(tools_last, dict):
        return []
    if any(key in tools_last for key in ("allowed", "blocked", "errors")):
        entries: list[dict] = []
        for key in ("allowed", "blocked", "errors"):
            values = tools_last.get(key) or []
            if isinstance(values, list):
                entries.extend([item for item in values if isinstance(item, dict)])
        return entries
    decisions = tools_last.get("decisions") or []
    if not isinstance(decisions, list):
        return []
    entries: list[dict] = []
    for entry in decisions:
        if isinstance(entry, dict):
            entries.append(_entry_from_decision(entry))
    return entries


def _summarize_skips(steps: list[dict], tool_summary: dict) -> dict:
    total = sum(1 for step in steps if step.get("kind") in SKIP_KINDS)
    branches = sum(1 for step in steps if step.get("kind") == "branch_skipped")
    cases = sum(1 for step in steps if step.get("kind") == "case_skipped")
    summary = {
        "total": total,
        "branches": branches,
        "cases": cases,
        "tools_blocked": tool_summary.get("blocked", 0),
    }
    return summary


def _run_ok(run_last: dict | None, execution_last: dict | None) -> bool | None:
    for pack in (run_last, execution_last):
        if isinstance(pack, dict) and "ok" in pack:
            return bool(pack.get("ok"))
    return None


def _status_from(ok: bool | None, tool_summary: dict, skipped_summary: dict) -> str:
    if ok is False:
        return "error"
    if tool_summary.get("blocked", 0) > 0 or tool_summary.get("error", 0) > 0:
        return "partial"
    if skipped_summary.get("total", 0) > 0:
        return "partial"
    return "ok"


def _return_summary(run_last: dict | None, returned: bool) -> str | None:
    if not returned or not isinstance(run_last, dict):
        return None
    if "result" not in run_last:
        return None
    return summarize_value(run_last.get("result"))


def _has_step_kind(steps: list[dict], kind: str) -> bool:
    return any(step.get("kind") == kind for step in steps)


def _step_line(step: dict) -> str | None:
    what = str(step.get("what") or "").strip()
    if not what:
        return None
    because = step.get("because")
    if because:
        return f"{_strip_period(what)} because {because}."
    return _ensure_period(what)


def _tool_blocked_line(entry: dict, *, verb: str) -> str:
    name = entry.get("tool") or "tool"
    reason = entry.get("reason")
    if reason and reason != "unknown":
        return f'tool "{name}" {verb} because {reason}.'
    return f'tool "{name}" {verb}. No explicit reason recorded.'


def _memory_skip_lines(memory_last: dict | None) -> list[str]:
    if not isinstance(memory_last, dict):
        return []
    events = memory_last.get("events") or []
    if not isinstance(events, list):
        return []
    lines: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        reason = event.get("reason") or event.get("explanation")
        if not reason:
            continue
        label = _memory_event_label(event_type)
        if not label:
            continue
        lines.append(f"{label} because {reason}.")
    return lines


def _memory_event_label(event_type: str | None) -> str | None:
    if event_type == "memory_denied":
        return "memory write denied"
    if event_type == "memory_deleted":
        return "memory deleted"
    if event_type == "memory_forget":
        return "memory forgotten"
    return None


def _strip_period(text: str) -> str:
    return text[:-1] if text.endswith(".") else text


def _ensure_period(text: str) -> str:
    return text if text.endswith(".") else f"{text}."


def _summary_text(flow_name: str, status: str) -> str:
    label = flow_name if flow_name else "flow"
    return f"Flow \"{label}\" status: {status}."


def _primary_tool(tool_entries: list[dict]) -> str | None:
    for entry in tool_entries:
        if entry.get("tool"):
            return str(entry.get("tool"))
    return None


def _entry_from_decision(entry: dict) -> dict:
    tool_name = str(entry.get("tool_name") or "tool")
    status = str(entry.get("status") or "")
    permission = entry.get("permission") if isinstance(entry.get("permission"), dict) else {}
    reasons = permission.get("reasons") if isinstance(permission.get("reasons"), list) else []
    capabilities = permission.get("capabilities_used") if isinstance(permission.get("capabilities_used"), list) else []
    reason = str(reasons[0]) if reasons else "unknown"
    capability = str(capabilities[0]) if capabilities else "none"
    result = status if status in {"ok", "blocked", "error"} else "ok"
    return {
        "tool": tool_name,
        "decision": "blocked" if result == "blocked" else "allowed",
        "capability": capability,
        "reason": reason,
        "result": result,
    }


def _load_last_run(root: Path) -> dict | None:
    return _load_json(root / ".namel3ss" / "run" / "last.json")


def _load_last_execution(root: Path) -> dict | None:
    return _load_json(root / ".namel3ss" / "execution" / "last.json")


def _load_last_tools(root: Path) -> dict | None:
    return _load_json(root / ".namel3ss" / "tools" / "last.json")


def _load_last_memory(root: Path) -> dict | None:
    return _load_json(root / ".namel3ss" / "memory" / "last.json")


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = ["API_VERSION", "build_flow_explain_pack", "write_flow_explain_artifacts"]
