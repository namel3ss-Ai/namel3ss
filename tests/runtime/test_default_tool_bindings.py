from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.executor import Executor
from namel3ss.config.model import AppConfig
from namel3ss.runtime.tools.bindings import load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from tests.conftest import lower_ir_program


def test_missing_bindings_file_returns_empty(tmp_path: Path) -> None:
    bindings = load_tool_bindings(tmp_path)
    assert bindings == {}


def test_default_bindings_not_used_when_file_exists(tmp_path: Path) -> None:
    write_tool_bindings(tmp_path, {"fetch_rate": ToolBinding(kind="python", entry="tools.fx_api:run")})
    bindings = load_tool_bindings(tmp_path)
    assert sorted(bindings.keys()) == ["fetch_rate"]


def test_resolve_tool_binding_falls_back_to_default(tmp_path: Path) -> None:
    resolved = resolve_tool_binding(tmp_path, "fetch_rate", AppConfig(), tool_kind="python", line=None, column=None)
    assert resolved.source == "default_binding"
    assert resolved.binding.entry == "tools.fx_api:run"


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
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["resolved_source"] == "default_binding"
