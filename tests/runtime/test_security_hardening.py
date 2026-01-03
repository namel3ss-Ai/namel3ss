from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.runner import run_flow
from namel3ss.config.model import AppConfig
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.secrets import collect_secret_values
from namel3ss.studio.api import execute_action
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


def _run_payload(tmp_path: Path, source: str, config: AppConfig) -> dict:
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    outcome = build_flow_payload(
        program,
        "demo",
        state={},
        input={},
        store=None,
        config=config,
        source=source,
        project_root=str(tmp_path),
    )
    return finalize_run_payload(outcome.payload, collect_secret_values(config))


def _expect_capability(payload: dict, capability: str) -> None:
    contract = payload.get("contract") or {}
    errors = contract.get("errors") or []
    assert errors, "Expected structured errors"
    assert errors[0].get("category") == "capability"
    traces = contract.get("traces") or []
    matches = [
        trace
        for trace in traces
        if trace.get("type") == "capability_check"
        and trace.get("capability") == capability
        and trace.get("allowed") is False
    ]
    assert matches, f"Missing denied capability_check for {capability}"


def test_capability_denies_filesystem_write(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "writer.py",
        "def run(payload):\n"
        "    path = payload.get(\"path\")\n"
        "    with open(path, \"w\", encoding=\"utf-8\") as handle:\n"
        "        handle.write(\"blocked\")\n"
        "    return {\"ok\": True}\n",
    )
    _bind_python_tool(tmp_path, "writer", "tools.writer:run")
    source = '''tool "writer":
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
'''
    config = AppConfig()
    config.capability_overrides = {"writer": {"no_filesystem_write": True}}
    payload = _run_payload(tmp_path, source, config)
    assert payload["contract"]["status"] == "error"
    _expect_capability(payload, "filesystem_write")


def test_capability_denies_network(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "fetcher.py",
        "from urllib import request\n\n"
        "def run(payload):\n"
        "    request.urlopen(payload.get(\"url\"))\n"
        "    return {\"ok\": True}\n",
    )
    _bind_python_tool(tmp_path, "fetcher", "tools.fetcher:run")
    source = '''tool "fetcher":
  implemented using python

  input:
    url is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is fetcher:
    url is "https://example.com"
  return result
'''
    config = AppConfig()
    config.capability_overrides = {"fetcher": {"no_network": True}}
    payload = _run_payload(tmp_path, source, config)
    assert payload["contract"]["status"] == "error"
    _expect_capability(payload, "network")


def test_capability_denies_env_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    _write_tool(
        tmp_path,
        "env_read.py",
        "import os\n\n"
        "def run(payload):\n"
        "    os.getenv(payload.get(\"key\"))\n"
        "    return {\"ok\": True}\n",
    )
    _bind_python_tool(tmp_path, "env reader", "tools.env_read:run")
    source = '''tool "env reader":
  implemented using python

  input:
    key is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is env reader:
    key is "OPENAI_API_KEY"
  return result
'''
    config = AppConfig()
    config.capability_overrides = {"env reader": {"no_env_read": True}}
    payload = _run_payload(tmp_path, source, config)
    assert payload["contract"]["status"] == "error"
    _expect_capability(payload, "env_read")


def test_capability_denies_subprocess(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "spawner.py",
        "import subprocess\n\n"
        "def run(payload):\n"
        "    subprocess.run([\"echo\", \"hi\"], check=False)\n"
        "    return {\"ok\": True}\n",
    )
    _bind_python_tool(tmp_path, "spawner", "tools.spawner:run")
    source = '''tool "spawner":
  implemented using python

  input:
    value is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is spawner:
    value is "hi"
  return result
'''
    config = AppConfig()
    config.capability_overrides = {"spawner": {"no_subprocess": True}}
    payload = _run_payload(tmp_path, source, config)
    assert payload["contract"]["status"] == "error"
    _expect_capability(payload, "subprocess")


def test_no_leaks_in_payloads_and_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-test-secret-1234"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    _write_tool(
        tmp_path,
        "leaker.py",
        "import os\n\n"
        "def run(payload):\n"
        "    token = payload.get(\"token\")\n"
        "    secret = os.getenv(\"OPENAI_API_KEY\")\n"
        "    raise ValueError(f\"boom {token} {secret}\")\n",
    )
    _bind_python_tool(tmp_path, "leaker", "tools.leaker:run")
    source = f'''tool "leaker":
  implemented using python

  input:
    token is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is leaker:
    token is "{secret}"
  return result

page "home":
  button "Run":
    calls flow "demo"
'''
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, sources = load_program(app_file.as_posix())
    with pytest.raises(Exception):
        run_flow(program, "demo", sources=sources)
    run_payload = json.loads((tmp_path / ".namel3ss" / "run" / "last.json").read_text(encoding="utf-8"))
    assert secret not in json.dumps(run_payload, sort_keys=True)
    execution_text = (tmp_path / ".namel3ss" / "execution" / "last.json").read_text(encoding="utf-8")
    assert secret not in execution_text

    studio_payload = execute_action(
        source,
        SessionState(),
        "page.home.button.run",
        {},
        app_path=app_file.as_posix(),
    )
    assert secret not in json.dumps(studio_payload, sort_keys=True)


def test_no_bypass_audit() -> None:
    root = Path(__file__).resolve().parents[2]
    client_text = (root / "src/namel3ss/runtime/ai/http/client.py").read_text(encoding="utf-8")
    assert "guard_network" in client_text
    for name in ("openai", "anthropic", "gemini", "mistral"):
        provider_text = (root / f"src/namel3ss/runtime/ai/providers/{name}.py").read_text(encoding="utf-8")
        assert "read_env" in provider_text
        tool_text = (root / f"src/namel3ss/runtime/providers/{name}/tool_calls_adapter.py").read_text(encoding="utf-8")
        assert "read_env" in tool_text
    shim_text = (root / "src/namel3ss/runtime/tools/runners/node/shim/index.js").read_text(encoding="utf-8")
    assert "configureCapabilities" in shim_text
    sandbox_text = (root / "src/namel3ss/runtime/tools/python_sandbox/bootstrap.py").read_text(encoding="utf-8")
    assert "os.open" in sandbox_text
