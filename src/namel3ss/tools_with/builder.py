from __future__ import annotations

from pathlib import Path

from namel3ss.tools_with.model import ToolsWithPack
from namel3ss.tools_with.normalize import stable_sort, write_tools_with_artifacts
from namel3ss.tools_with.render_plain import render_with

MAX_ENTRIES = 50


def build_tools_with_pack(traces: list, *, project_root: str | None) -> ToolsWithPack:
    events = _tool_call_events(traces)
    allowed, blocked, errors = _categorize(events)
    notes: list[str] = []
    allowed, notes = _truncate("allowed", stable_sort(allowed), notes)
    blocked, notes = _truncate("blocked", stable_sort(blocked), notes)
    errors, notes = _truncate("errors", stable_sort(errors), notes)
    pack = ToolsWithPack(
        tools_called=len(events),
        allowed=allowed,
        blocked=blocked,
        errors=errors,
        none_used=len(events) == 0,
        notes=notes,
    )
    if project_root:
        plain = render_with(pack)
        write_tools_with_artifacts(Path(project_root), pack, plain, plain)
    return pack


def _tool_call_events(traces: list) -> list[dict]:
    result: list[dict] = []
    for trace in traces or []:
        if isinstance(trace, dict) and trace.get("type") == "tool_call":
            result.append(trace)
    return result


def _categorize(events: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    allowed: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []
    for event in events:
        entry = _entry_from_event(event)
        result = entry.get("result")
        if result == "blocked":
            blocked.append(entry)
        elif result == "error":
            errors.append(entry)
        else:
            allowed.append(entry)
    return allowed, blocked, errors


def _entry_from_event(event: dict) -> dict:
    tool = event.get("tool") or event.get("tool_name") or "tool"
    result = event.get("result") or event.get("status") or "ok"
    decision = event.get("decision")
    if not decision:
        decision = "blocked" if result == "blocked" else "allowed"
    return {
        "tool": str(tool),
        "decision": str(decision),
        "capability": str(event.get("capability") or "none"),
        "reason": str(event.get("reason") or "unknown"),
        "result": str(result),
    }


def _truncate(label: str, entries: list[dict], notes: list[str]) -> tuple[list[dict], list[str]]:
    if len(entries) <= MAX_ENTRIES:
        return entries, notes
    notes = list(notes)
    notes.append(f"{label} entries truncated at {MAX_ENTRIES}.")
    return entries[:MAX_ENTRIES], notes


__all__ = ["build_tools_with_pack"]
