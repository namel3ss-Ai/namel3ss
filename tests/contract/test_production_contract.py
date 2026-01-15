from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.runner import run_flow
from namel3ss.production_contract import PRODUCTION_CONTRACT_VERSION, canonical_trace_json, validate_run_contract
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.studio.api import execute_action
from namel3ss.studio.session import SessionState
from namel3ss.traces.schema import TRACE_VERSION


APP_SOURCE = '''
spec is "1.0"

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


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


CAPABILITY_SOURCE = '''
spec is "1.0"

tool "fetch":
  implemented using python

  input:
    url is text

  output:
    ok is boolean

flow "demo":
  let result is fetch:
    url is "https://example.com"
  return result

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


TOOL_ERROR_SOURCE = '''
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


def test_run_contract_cli_and_studio(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    cli_payload = run_flow(program, "demo")
    assert validate_run_contract(cli_payload) == []

    session = SessionState()
    studio_payload = execute_action(
        APP_SOURCE,
        session,
        "page.home.button.run",
        {},
        app_path=app_file.as_posix(),
    )
    assert validate_run_contract(studio_payload) == []

    assert cli_payload["contract"].keys() == studio_payload["contract"].keys()


def test_trace_contract_canonical_json(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(TRACE_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    payload = run_flow(program, "demo")
    assert validate_run_contract(payload) == []

    traces = payload["contract"]["traces"]
    assert traces
    first = canonical_trace_json(traces)
    second = canonical_trace_json(traces)
    assert first == second


def test_capability_contract_blocked_tool(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(CAPABILITY_SOURCE, encoding="utf-8")

    (tmp_path / "namel3ss.toml").write_text(
        '[capability_overrides]\n"fetch" = { no_network = true }\n',
        encoding="utf-8",
    )
    write_tool_bindings(
        tmp_path,
        {"fetch": ToolBinding(kind="python", entry="tools.fetch:run", runner="service", url="http://service.local")},
    )

    program, _ = load_program(app_file.as_posix())
    with pytest.raises(Exception):
        run_flow(program, "demo")

    payload = _load_last_run(tmp_path)
    assert validate_run_contract(payload) == []
    errors = payload["contract"]["errors"]
    assert errors
    assert errors[0]["category"] == "capability"
    traces = payload["contract"]["traces"]
    assert any(trace.get("type") == "capability_check" for trace in traces)


def test_error_contract_structured(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(TOOL_ERROR_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    with pytest.raises(Exception):
        run_flow(program, "demo")

    payload = _load_last_run(tmp_path)
    assert validate_run_contract(payload) == []
    errors = payload["contract"]["errors"]
    assert errors
    assert errors[0]["category"] == "policy"
    assert errors[0]["code"]
    location = errors[0].get("location") or {}
    assert location.get("line") is not None


def test_ai_trace_requires_boundary_events() -> None:
    payload = {
        "ok": True,
        "contract": {
            "schema_version": PRODUCTION_CONTRACT_VERSION,
            "trace_schema_version": TRACE_VERSION,
            "status": "ok",
            "flow_name": "demo",
            "errors": [],
            "state": {},
            "result": None,
            "traces": [{"type": "ai_call", "canonical_events": [], "memory_events": []}],
            "memory": {"events": [], "count": 0},
        },
    }
    issues = validate_run_contract(payload)
    assert any("ai_call boundaries" in issue for issue in issues)


def _load_last_run(root: Path) -> dict:
    path = root / ".namel3ss" / "run" / "last.json"
    return json.loads(path.read_text(encoding="utf-8"))
