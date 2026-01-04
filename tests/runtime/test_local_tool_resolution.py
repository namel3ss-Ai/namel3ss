from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from tests.conftest import lower_ir_program


def test_local_tool_resolution_and_execution(tmp_path: Path) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "dummy_tool.py").write_text(
        "def run(payload):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )

    resolved = resolve_tool_binding(tmp_path, "dummy tool", AppConfig(), tool_kind="python", line=None, column=None)
    assert resolved.source == "binding"
    assert resolved.binding.entry == "tools.dummy_tool:run"
    assert resolved.pack_paths is not None
    assert tmp_path in resolved.pack_paths

    source = '''tool "dummy tool":
  implemented using python

  input:
    payload is json

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is dummy tool:
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
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["resolved_source"] == "binding"
