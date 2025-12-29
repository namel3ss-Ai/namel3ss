from __future__ import annotations

import json
from pathlib import Path

from .collector import collect_tool_decisions
from .decision import ToolDecision
from .normalize import build_plain_text, write_last_tools
from .render_plain import render_with

API_VERSION = "tools.v1"


def build_tool_explain_pack(execution_last: dict | None, run_last: dict | None) -> dict:
    decisions = collect_tool_decisions(execution_last=execution_last, run_payload=run_last)
    return _pack_from_decisions(decisions, run_last)


def build_tool_explain_bundle(root: Path) -> tuple[dict, list[ToolDecision]] | None:
    run_last = _load_last_run(root)
    if run_last is None:
        return None
    execution_last = _load_last_execution(root)
    decisions = collect_tool_decisions(execution_last=execution_last, run_payload=run_last)
    pack = _pack_from_decisions(decisions, run_last)
    return pack, decisions


def write_tool_explain_artifacts(root: Path, pack: dict, decisions: list[ToolDecision]) -> None:
    text = render_with(decisions)
    plain = build_plain_text(pack)
    write_last_tools(root, pack, plain, text)


def _pack_from_decisions(decisions: list[ToolDecision], run_last: dict | None) -> dict:
    counts = _count_decisions(decisions)
    summary = _summary_text(counts)
    ok = True
    if isinstance(run_last, dict):
        ok = bool(run_last.get("ok", True))
    return {
        "ok": ok,
        "api_version": API_VERSION,
        "decisions": [decision.as_dict() for decision in decisions],
        "summary": summary,
        "counts": counts,
    }


def _count_decisions(decisions: list[ToolDecision]) -> dict:
    counts = {"total": len(decisions), "ok": 0, "error": 0, "blocked": 0}
    for decision in decisions:
        if decision.status == "ok":
            counts["ok"] += 1
        elif decision.status == "blocked":
            counts["blocked"] += 1
        elif decision.status == "error":
            counts["error"] += 1
    return counts


def _summary_text(counts: dict) -> str:
    return (
        f"Tools: {counts.get('total')} total, {counts.get('ok')} ok, "
        f"{counts.get('blocked')} blocked, {counts.get('error')} error."
    )


def _load_last_run(root: Path) -> dict | None:
    path = root / ".namel3ss" / "run" / "last.json"
    return _load_json(path)


def _load_last_execution(root: Path) -> dict | None:
    path = root / ".namel3ss" / "execution" / "last.json"
    return _load_json(path)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


__all__ = ["API_VERSION", "build_tool_explain_pack", "build_tool_explain_bundle", "write_tool_explain_artifacts"]
