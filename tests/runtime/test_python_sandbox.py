from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


def _write_tool(tmp_path: Path, filename: str, body: str) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / filename).write_text(body, encoding="utf-8")


def _write_bindings(tmp_path: Path, tool_name: str, entry: str) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "tools.yaml").write_text(
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        f'    entry: "{entry}"\n'
        "    sandbox: true\n",
        encoding="utf-8",
    )


def _run_blocked(source: str, config: AppConfig, tmp_path: Path) -> list[dict[str, object]]:
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={},
        config=config,
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    return [event for event in executor.traces if isinstance(event, dict)]


def _expect_block(traces: list[dict[str, object]], capability: str) -> None:
    for event in traces:
        if event.get("type") == "capability_check" and event.get("capability") == capability:
            assert event.get("allowed") is False
            return
    raise AssertionError(f"Missing capability_check for {capability}")


def test_python_sandbox_blocks_filesystem_write(tmp_path: Path) -> None:
    source = '''tool "user writes file":
  implemented using python

  input:
    path is text

  output:
    ok is boolean

flow "demo":
  let result is user writes file:
    path is "blocked.txt"
  return result
'''
    _write_tool(
        tmp_path,
        "user_file.py",
        "def run(payload):\n"
        "    path = payload.get(\"path\")\n"
        "    with open(path, \"w\", encoding=\"utf-8\") as handle:\n"
        "        handle.write(\"blocked\")\n"
        "    return {\"ok\": True}\n",
    )
    _write_bindings(tmp_path, "user writes file", "tools.user_file:run")
    config = AppConfig()
    config.capability_overrides = {"user writes file": {"no_filesystem_write": True}}
    traces = _run_blocked(source, config, tmp_path)
    _expect_block(traces, "filesystem_write")
    assert not (tmp_path / "blocked.txt").exists()


def test_python_sandbox_blocks_network(tmp_path: Path) -> None:
    source = '''tool "user fetches web":
  implemented using python

  input:
    url is text

  output:
    ok is boolean

flow "demo":
  let result is user fetches web:
    url is "https://example.com"
  return result
'''
    _write_tool(
        tmp_path,
        "user_net.py",
        "from urllib import request\n\n"
        "def run(payload):\n"
        "    url = payload.get(\"url\")\n"
        "    request.urlopen(url)\n"
        "    return {\"ok\": True}\n",
    )
    _write_bindings(tmp_path, "user fetches web", "tools.user_net:run")
    config = AppConfig()
    config.capability_overrides = {"user fetches web": {"no_network": True}}
    traces = _run_blocked(source, config, tmp_path)
    _expect_block(traces, "network")
