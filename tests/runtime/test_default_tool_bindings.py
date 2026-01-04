from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from tests.conftest import lower_ir_program


def test_default_bindings_used_when_missing(tmp_path: Path) -> None:
    bindings = load_tool_bindings(tmp_path)
    assert bindings["fetch_rate"].entry == "tools.fx_api:run"
    assert bindings["fetch_weather"].entry == "tools.weather_api:run"
    assert bindings["greeter"].entry == "tests.fixtures.tools.sample_tool:greet"


def test_default_bindings_not_used_when_file_exists(tmp_path: Path) -> None:
    write_tool_bindings(tmp_path, {"fetch_rate": ToolBinding(kind="python", entry="tools.fx_api:run")})
    bindings = load_tool_bindings(tmp_path)
    assert sorted(bindings.keys()) == ["fetch_rate"]


def test_default_binding_executes_greeter(tmp_path: Path) -> None:
    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text
    ok is boolean

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"message": "Hello Ada", "ok": True}
