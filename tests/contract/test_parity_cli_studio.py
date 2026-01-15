from __future__ import annotations

from pathlib import Path
import shutil

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.runner import run_flow
from namel3ss.cli.ui_mode import run_action
from namel3ss.config.loader import load_config
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.studio.api import execute_action, get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.validation_entrypoint import build_static_manifest


APP_SOURCE = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock"

record "User":
  name string must be present

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply

page "home":
  button "Run":
    calls flow "demo"
  form is "User"
'''.lstrip()

DECLARATIVE_SOURCE = '''
spec is "1.0"

record "Note":
  name is text

flow "create_note"
  input
    name is text
  create "Note"
    name is input.name

page "home":
  button "Add":
    calls flow "create_note"
'''.lstrip()


def _assert_parity(cli_payload: dict, studio_payload: dict) -> None:
    assert cli_payload["ok"] == studio_payload["ok"]
    assert "result" in cli_payload
    assert "result" in studio_payload
    cli_contract = cli_payload["contract"]
    studio_contract = studio_payload["contract"]
    assert cli_contract["status"] == studio_contract["status"]
    assert cli_contract["errors"] == studio_contract["errors"]
    assert cli_contract["trace_hash"] == studio_contract["trace_hash"]
    assert cli_contract["trace_schema_version"] == studio_contract["trace_schema_version"]
    assert cli_contract["state"] == studio_contract["state"]
    assert cli_contract["result"] == studio_contract["result"]
    cli_types = [trace.get("type") for trace in cli_contract.get("traces", [])]
    studio_types = [trace.get("type") for trace in studio_contract.get("traces", [])]
    assert cli_types == studio_types


def test_cli_studio_parity_call_flow(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    program, sources = load_program(app_file.as_posix())

    _reset_memory(tmp_path)
    cli_payload = run_flow(program, "demo", sources=sources)

    _reset_memory(tmp_path)
    session = SessionState()
    studio_payload = execute_action(
        APP_SOURCE,
        session,
        "page.home.button.run",
        {},
        app_path=app_file.as_posix(),
    )

    _assert_parity(cli_payload, studio_payload)


def test_cli_studio_parity_submit_form_error(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())

    cli_payload = run_action(program, "page.home.form.user", {})

    studio_payload = execute_action(
        APP_SOURCE,
        SessionState(),
        "page.home.form.user",
        {},
        app_path=app_file.as_posix(),
    )

    _assert_parity(cli_payload, studio_payload)
    assert cli_payload["ok"] is False
    assert studio_payload["ok"] is False
    assert cli_payload["result"] is None
    assert studio_payload["result"] is None
    assert cli_payload.get("errors") == studio_payload.get("errors")


def _reset_memory(root: Path) -> None:
    memory_dir = root / ".namel3ss" / "memory"
    if memory_dir.exists():
        shutil.rmtree(memory_dir)


def test_static_manifest_helper_matches_studio(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    config = load_config(app_path=app_file)
    warnings: list = []
    helper_manifest = build_static_manifest(program, config=config, state={}, store=MemoryStore(), warnings=warnings)

    studio_manifest = get_ui_payload(APP_SOURCE, SessionState(), app_path=app_file.as_posix())

    assert helper_manifest.get("pages") == studio_manifest.get("pages")
    studio_warnings = studio_manifest.get("warnings") or []
    assert len(warnings) == len(studio_warnings)


def test_cli_studio_parity_declarative_action(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(DECLARATIVE_SOURCE, encoding="utf-8")
    program, sources = load_program(app_file.as_posix())
    payload = {"name": "Ada"}

    cli_payload = run_action(program, "page.home.button.add", payload)

    studio_payload = execute_action(
        DECLARATIVE_SOURCE,
        SessionState(),
        "page.home.button.add",
        payload,
        app_path=app_file.as_posix(),
    )

    _assert_parity(cli_payload, studio_payload)
    cli_flow = [trace for trace in cli_payload["contract"]["traces"] if trace.get("type") in {"flow_start", "flow_step"}]
    studio_flow = [trace for trace in studio_payload["contract"]["traces"] if trace.get("type") in {"flow_start", "flow_step"}]
    assert cli_flow == studio_flow


def test_static_manifest_declarative_warning_parity(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

record "Note":
  name is text

flow "create_note"
  require "manual review"
  create "Note"
    name is "Ada"

page "home":
  button "Add":
    calls flow "create_note"
'''.lstrip()
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    config = load_config(app_path=app_file)
    warnings: list = []
    build_static_manifest(program, config=config, state={}, store=MemoryStore(), warnings=warnings)

    studio_manifest = get_ui_payload(source, SessionState(), app_path=app_file.as_posix())
    studio_warnings = studio_manifest.get("warnings") or []

    assert len(warnings) == len(studio_warnings)
    assert warnings[0].code == studio_warnings[0].get("code")
