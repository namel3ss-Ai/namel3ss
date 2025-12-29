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


def test_tool_calls_flow_through_gate(monkeypatch, tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    _write_tool(tmp_path)
    write_tool_bindings(
        tmp_path,
        {"greeter": ToolBinding(kind="python", entry="tools.greeter:run")},
    )
    gate_called = {"value": False}

    import namel3ss.runtime.tools.executor as tools_executor

    real_gate = tools_executor.gate_tool_call

    def gate_wrapper(*args, **kwargs):
        gate_called["value"] = True
        return real_gate(*args, **kwargs)

    def fake_execute_python_tool_call(ctx, *, tool_name: str, payload: object, line, column):
        assert gate_called["value"] is True
        return {"message": "ok"}

    monkeypatch.setattr(tools_executor, "gate_tool_call", gate_wrapper)
    monkeypatch.setattr(tools_executor, "execute_python_tool_call", fake_execute_python_tool_call)

    executor = Executor(
        program.flows[0],
        tools=program.tools,
        input_data={},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"message": "ok"}
