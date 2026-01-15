from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.runner import run_flow


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''.lstrip()


def _run_once(root: Path) -> str:
    program, _ = load_program((root / "app.ai").as_posix())
    run_flow(program, "demo")
    run_path = root / ".namel3ss" / "run" / "last.json"
    return run_path.read_text(encoding="utf-8")


def test_run_artifact_is_stable_and_scrubbed(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(SOURCE, encoding="utf-8")

    first = _run_once(tmp_path)
    second = _run_once(tmp_path)

    assert first == second
    payload = json.loads(first)
    text = first.lower()
    for key in ("timestamp", "time_start", "time_end", "call_id", "duration_ms", "trace_id"):
        assert key not in text
    contract = payload.get("contract") or {}
    assert contract.get("trace_hash")
