from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.execution.builder import build_execution_graph
from namel3ss.runtime.execution.render_plain import render_how


def run_how_command(args: list[str]) -> int:
    if args:
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for how.",
                why="how does not accept extra input.",
                fix="Run n3 how.",
                example="n3 how",
            )
        )
    _run_how()
    return 0


def _run_how() -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    last_json = project_root / ".namel3ss" / "execution" / "last.json"
    if not last_json.exists():
        print("No execution run found yet. Try: n3 run app.ai")
        return
    payload = json.loads(last_json.read_text(encoding="utf-8"))
    graph = build_execution_graph(payload)
    text = render_how(graph)
    _write_last_how(project_root, text)
    print(text)


def _write_last_how(project_root: Path, text: str) -> None:
    execution_dir = project_root / ".namel3ss" / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)
    last_how = execution_dir / "last.how.txt"
    last_how.write_text(text.rstrip() + "\n", encoding="utf-8")


__all__ = ["run_how_command"]
