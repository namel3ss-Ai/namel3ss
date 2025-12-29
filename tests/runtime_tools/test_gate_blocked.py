from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from tests.conftest import lower_ir_program


SOURCE = '''tool "blocked tool":
  implemented using python

  input:
    name is text

  output:
    message is text

spec is "1.0"

flow "demo":
  let result is blocked tool:
    name is "Ada"
  return result
'''


def _write_tool(root: Path) -> None:
    tools_dir = root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "blocked_tool.py").write_text(
        "def run(payload):\n    return {'message': 'hi'}\n",
        encoding="utf-8",
    )


def test_gate_blocks_denied_capability(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    program.tools["blocked tool"].capabilities = ("network",)
    _write_tool(tmp_path)
    write_tool_bindings(
        tmp_path,
        {"blocked tool": ToolBinding(kind="python", entry="tools.blocked_tool:run")},
    )
    config = AppConfig()
    config.capability_overrides = {"blocked tool": {"no_network": True}}
    executor = Executor(
        program.flows[0],
        tools=program.tools,
        input_data={},
        project_root=str(tmp_path),
        config=config,
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    tool_event = next(
        event for event in executor.traces if isinstance(event, dict) and event.get("type") == "tool_call"
    )
    assert tool_event["decision"] == "blocked"
    assert tool_event["reason"] == "policy_denied"
    assert tool_event["capability"] == "network"
    assert tool_event["result"] == "blocked"
