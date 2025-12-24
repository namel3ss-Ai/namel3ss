from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from tests.conftest import lower_ir_program


def test_tool_pack_slugify_executes(tmp_path: Path) -> None:
    source = '''tool "text.slugify":
  implemented using python

  input:
    text is text

  output:
    text is text

flow "demo":
  let result is text.slugify:
    text is input.text
  return result
'''
    program = lower_ir_program(source)
    write_tool_bindings(tmp_path, {"text.slugify": ToolBinding(kind="python", entry="namel3ss.tool_packs.text:slugify")})
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"text": "Hello World"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"text": "hello-world"}
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["python_env"] == "system"
    assert tool_event["python_path"] == sys.executable
    assert tool_event["protocol_version"] == 1
