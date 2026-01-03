from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.secrets import collect_secret_values
from namel3ss.studio.api import execute_action, get_summary_payload
from namel3ss.studio.session import SessionState


def _write_tool(tmp_path: Path, filename: str, body: str) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / filename).write_text(body, encoding="utf-8")


def _bind_python_tool(tmp_path: Path, tool_name: str, entry: str) -> None:
    write_tool_bindings(
        tmp_path,
        {
            tool_name: ToolBinding(
                kind="python",
                entry=entry,
                runner="local",
                sandbox=True,
            )
        },
    )


def _run_payload(tmp_path: Path, source: str, *, flow_name: str = "demo") -> dict:
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    config = load_config(app_path=app_file, root=tmp_path)
    outcome = build_flow_payload(
        program,
        flow_name,
        state={},
        input={},
        store=None,
        config=config,
        source=source,
        project_root=str(tmp_path),
    )
    return finalize_run_payload(outcome.payload, collect_secret_values(config))


def _error_entry(payload: dict) -> dict:
    contract = payload.get("contract") or {}
    errors = contract.get("errors") or []
    assert errors, "Expected structured contract errors"
    return errors[0]


def _assert_entry(entry: dict, category: str) -> None:
    assert entry.get("category") == category
    assert isinstance(entry.get("code"), str) and entry.get("code")
    assert isinstance(entry.get("message"), str) and entry.get("message")


def test_error_category_parse() -> None:
    source = 'spec is "1.0"\nflow "demo":\n  let is 1\n'
    payload = get_summary_payload(source, "")
    entry = payload.get("error_entry") or {}
    _assert_entry(entry, "parse")
    location = entry.get("location") or {}
    assert location.get("line") is not None


def test_error_category_runtime(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

flow "demo":
  let result is 1 / 0
  return result
'''.lstrip()
    payload = _run_payload(tmp_path, source)
    entry = _error_entry(payload)
    _assert_entry(entry, "runtime")


def test_error_category_tool(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "boom.py",
        "def run(payload):\n"
        "    raise ValueError('boom')\n",
    )
    _bind_python_tool(tmp_path, "boom", "tools.boom:run")
    source = '''
tool "boom":
  implemented using python

  input:
    value is text

  output:
    value is text

spec is "1.0"

flow "demo":
  let result is boom:
    value is "hi"
  return result
'''.lstrip()
    payload = _run_payload(tmp_path, source)
    entry = _error_entry(payload)
    _assert_entry(entry, "tool")


def test_error_category_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = '''
ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''.lstrip()
    body = json.dumps({"error": {"code": "invalid_api_key", "type": "invalid_request_error"}}).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        raise HTTPError(url=req.get_full_url(), code=401, msg="Unauthorized", hdrs=None, fp=io.BytesIO(body))

    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setattr("namel3ss.runtime.ai.http.client.urlopen", fake_urlopen)
    payload = _run_payload(tmp_path, source)
    entry = _error_entry(payload)
    _assert_entry(entry, "provider")


def test_error_category_capability(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "writer.py",
        "def run(payload):\n"
        "    path = payload.get('path')\n"
        "    with open(path, 'w', encoding='utf-8') as handle:\n"
        "        handle.write('blocked')\n"
        "    return {'ok': True}\n",
    )
    _bind_python_tool(tmp_path, "writer", "tools.writer:run")
    (tmp_path / "namel3ss.toml").write_text(
        '[capability_overrides]\n"writer" = { no_filesystem_write = true }\n',
        encoding="utf-8",
    )
    source = '''
tool "writer":
  implemented using python

  input:
    path is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is writer:
    path is "blocked.txt"
  return result
'''.lstrip()
    payload = _run_payload(tmp_path, source)
    entry = _error_entry(payload)
    _assert_entry(entry, "capability")


def test_error_category_policy(tmp_path: Path) -> None:
    source = '''
tool "missing":
  implemented using python

  input:
    value is text

  output:
    value is text

spec is "1.0"

flow "demo":
  let result is missing:
    value is "hi"
  return result
'''.lstrip()
    payload = _run_payload(tmp_path, source)
    entry = _error_entry(payload)
    _assert_entry(entry, "policy")


def test_no_traceback_and_no_leaks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-test-secret-9876"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    _write_tool(
        tmp_path,
        "noisy.py",
        "def run(payload):\n"
        "    raise RuntimeError('Traceback (most recent call last): ' + payload.get('token'))\n",
    )
    _bind_python_tool(tmp_path, "noisy", "tools.noisy:run")
    source = f'''
tool "noisy":
  implemented using python

  input:
    token is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is noisy:
    token is "{secret}"
  return result
'''.lstrip()
    payload = _run_payload(tmp_path, source)
    serialized = json.dumps(payload, sort_keys=True)
    assert "Traceback" not in serialized
    assert secret not in serialized
    errors_path = tmp_path / ".namel3ss" / "errors" / "last.json"
    if errors_path.exists():
        text = errors_path.read_text(encoding="utf-8")
        assert "Traceback" not in text
        assert secret not in text


def test_error_determinism(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

flow "demo":
  let result is 1 / 0
  return result
'''.lstrip()
    first = _run_payload(tmp_path, source)
    second = _run_payload(tmp_path, source)
    assert first["contract"]["errors"] == second["contract"]["errors"]
    assert first["contract"]["trace_hash"] == second["contract"]["trace_hash"]


def test_error_parity_cli_studio(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

flow "demo":
  let result is 1 / 0
  return result

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    cli_payload = _run_payload(tmp_path, source)
    session = SessionState()
    studio_payload = execute_action(source, session, "page.home.button.run", {}, app_path=app_file.as_posix())

    assert cli_payload["contract"]["errors"] == studio_payload["contract"]["errors"]
    assert cli_payload["contract"]["trace_hash"] == studio_payload["contract"]["trace_hash"]
