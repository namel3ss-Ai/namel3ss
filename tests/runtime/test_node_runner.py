from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.runners.node.protocol import run_node_subprocess
from namel3ss.runtime.tools.runners.node.runner import DEFAULT_NODE_TOOL_TIMEOUT_SECONDS
from tests.conftest import lower_ir_program


def _node_available() -> bool:
    return shutil.which("node") is not None


def _write_node_tool(tmp_path: Path, name: str, body: str) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / f"{name}.js").write_text(body, encoding="utf-8")


def _write_node_bindings(tmp_path: Path, tool_name: str, entry: str) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "tools.yaml").write_text(
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "node"\n'
        f'    entry: "{entry}"\n'
        '    runner: "node"\n',
        encoding="utf-8",
    )


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_node_runner_executes_tool(tmp_path: Path) -> None:
    _write_node_tool(tmp_path, "greeter", 'exports.run = (payload) => ({ message: `hi ${payload.name}` });\n')
    _write_node_bindings(tmp_path, "greeter", "tools.greeter:run")
    source = '''tool "greeter":
  implemented using node

  input:
    name is text

  output:
    message is text

spec is "1.0"

flow "demo":
  let result is greeter:
    name is "Ada"
  return result
'''
    program = lower_ir_program(source)
    executor = Executor(program.flows[0], schemas={}, tools=program.tools, project_root=str(tmp_path))
    result = executor.run()
    assert result.last_value == {"message": "hi Ada"}
    events = [event for event in executor.traces if isinstance(event, dict)]
    assert any(event.get("type") == "tool_call" and event.get("runner") == "node" for event in events)


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_node_runner_returns_stable_error(tmp_path: Path) -> None:
    _write_node_tool(tmp_path, "bad", 'exports.run = () => { throw new Error("boom"); };\n')
    node_path = Path(shutil.which("node"))
    result = run_node_subprocess(
        node_path=node_path,
        tool_name="bad",
        entry="tools.bad:run",
        payload={},
        app_root=tmp_path,
        timeout_seconds=2,
    )
    assert result.ok is False
    assert result.error_type == "Error"
    assert result.error_message == "boom"


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_node_default_timeout_applies_when_unset(tmp_path: Path) -> None:
    _write_node_tool(tmp_path, "quick", "exports.run = () => ({ ok: true });\n")
    _write_node_bindings(tmp_path, "quick", "tools.quick:run")
    source = '''tool "quick":
  implemented using node

  input:
    payload is json

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is quick:
    payload is input.payload
  return result
'''
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"value": 1}},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"ok": True}
    tool_event = next(
        event for event in executor.traces if isinstance(event, dict) and event.get("type") == "tool_call"
    )
    assert tool_event["timeout_ms"] == DEFAULT_NODE_TOOL_TIMEOUT_SECONDS * 1000


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_node_timeout_message_reports_configured_timeout(tmp_path: Path) -> None:
    _write_node_tool(
        tmp_path,
        "slow",
        "exports.run = () => new Promise((resolve) => setTimeout(() => resolve({ ok: true }), 5000));\n",
    )
    node_path = Path(shutil.which("node"))
    with pytest.raises(Namel3ssError) as excinfo:
        run_node_subprocess(
            node_path=node_path,
            tool_name="slow",
            entry="tools.slow:run",
            payload={},
            app_root=tmp_path,
            timeout_seconds=1,
        )
    assert "Tool exceeded 1s timeout." in str(excinfo.value)


def test_node_capability_blocked_without_sandbox(tmp_path: Path) -> None:
    _write_node_bindings(tmp_path, "fetch", "tools.fetch:run")
    source = '''tool "fetch":
  implemented using node

  input:
    url is text

  output:
    status is number
    data is json

spec is "1.0"

flow "demo":
  let result is fetch:
    url is "https://example.com/data"
  return result
'''
    program = lower_ir_program(source)
    config = AppConfig()
    config.capability_overrides = {"fetch": {"no_network": True}}
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        config=config,
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    checks = [event for event in executor.traces if isinstance(event, dict) and event.get("type") == "capability_check"]
    assert any(check.get("capability") == "network" and check.get("allowed") is False for check in checks)
