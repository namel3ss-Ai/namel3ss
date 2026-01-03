from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.runner import run_flow
from namel3ss.determinism import canonical_run_json, canonical_trace_json, trace_hash
from namel3ss.studio.api import execute_action
from namel3ss.studio.session import SessionState


TRACE_SOURCE = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock"

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


ERROR_SOURCE = '''
spec is "1.0"

tool "missing":
  implemented using python

  input:
    value is text

  output:
    value is text

flow "demo":
  let result is missing:
    value is "hi"
  return result

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


def test_determinism_repeatable_trace_and_outcome(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(TRACE_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    snapshots = []
    for _ in range(3):
        _reset_memory(tmp_path)
        payload = run_flow(program, "demo")
        snapshots.append(_snapshot(payload))

    first = snapshots[0]
    for snapshot in snapshots[1:]:
        assert snapshot == first


def test_determinism_cli_studio_cross_path(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(TRACE_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    _reset_memory(tmp_path)
    cli_payload = run_flow(program, "demo")

    _reset_memory(tmp_path)
    session = SessionState()
    studio_payload = execute_action(
        TRACE_SOURCE,
        session,
        "page.home.button.run",
        {},
        app_path=app_file.as_posix(),
    )

    assert cli_payload["contract"]["trace_hash"] == studio_payload["contract"]["trace_hash"]
    assert canonical_run_json(cli_payload) == canonical_run_json(studio_payload)


def test_error_payload_deterministic(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(ERROR_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    payloads = []
    for _ in range(2):
        _reset_memory(tmp_path)
        with pytest.raises(Exception):
            run_flow(program, "demo")
        payloads.append(_load_last_run(tmp_path))

    assert canonical_run_json(payloads[0]) == canonical_run_json(payloads[1])
    assert payloads[0]["contract"]["errors"] == payloads[1]["contract"]["errors"]


def _snapshot(payload: dict) -> dict:
    traces = payload.get("traces") if isinstance(payload, dict) else None
    trace_list = traces if isinstance(traces, list) else []
    contract_hash = payload.get("contract", {}).get("trace_hash")
    recomputed = trace_hash(trace_list)
    assert contract_hash == recomputed
    return {
        "canonical_trace": canonical_trace_json(trace_list),
        "trace_hash": contract_hash,
        "trace_hash_recomputed": recomputed,
        "canonical_run": canonical_run_json(payload),
    }


def _load_last_run(root: Path) -> dict:
    path = root / ".namel3ss" / "run" / "last.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _reset_memory(root: Path) -> None:
    memory_dir = root / ".namel3ss" / "memory"
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
