from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.explain.builder import build_tool_explain_bundle, write_tool_explain_artifacts
from namel3ss.runtime.tools.explain.decision import ToolDecision
from namel3ss.runtime.tools.explain.render_plain import render_with


def run_with_command(args: list[str]) -> int:
    if args:
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for with.",
                why="with does not accept extra input.",
                fix="Run n3 with.",
                example="n3 with",
            )
        )
    _run_with()
    return 0


def _run_with() -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    tools_dir = project_root / ".namel3ss" / "tools"
    last_json = tools_dir / "last.json"
    last_text = tools_dir / "last.with.txt"
    if last_json.exists():
        if last_text.exists():
            print(last_text.read_text(encoding="utf-8").rstrip())
            return
        payload = json.loads(last_json.read_text(encoding="utf-8"))
        decisions = _decisions_from_payload(payload)
        text = render_with(decisions)
        tools_dir.mkdir(parents=True, exist_ok=True)
        last_text.write_text(text.rstrip() + "\n", encoding="utf-8")
        print(text)
        return
    bundle = build_tool_explain_bundle(project_root)
    if bundle is None:
        print("No run found yet. Try: n3 run app.ai")
        return
    pack, decisions = bundle
    write_tool_explain_artifacts(project_root, pack, decisions)
    print(render_with(decisions))


def _decisions_from_payload(payload: dict) -> list[ToolDecision]:
    decisions = payload.get("decisions") or []
    result: list[ToolDecision] = []
    for entry in decisions:
        if isinstance(entry, dict):
            result.append(ToolDecision.from_dict(entry))
    return result


__all__ = ["run_with_command"]
