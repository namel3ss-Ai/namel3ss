from pathlib import Path

from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from tests.conftest import lower_ir_program


SOURCE = '''tool "greeter":
  implemented using python

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


def _write_tool(root: Path) -> None:
    tools_dir = root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "greeter.py").write_text(
        "def run(payload):\n    return {'message': f\"Hello {payload.get('name', '')}\"}\n",
        encoding="utf-8",
    )


def test_gate_allows_tool_call(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    program.tools["greeter"].capabilities = ("network",)
    _write_tool(tmp_path)
    write_tool_bindings(
        tmp_path,
        {"greeter": ToolBinding(kind="python", entry="tools.greeter:run")},
    )
    executor = Executor(
        program.flows[0],
        tools=program.tools,
        input_data={},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"message": "Hello Ada"}
    tool_event = next(
        event for event in result.traces if isinstance(event, dict) and event.get("type") == "tool_call"
    )
    assert tool_event["decision"] == "allowed"
    assert tool_event["result"] == "ok"
