from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


def test_no_wiring_story(tmp_path: Path, monkeypatch, capsys) -> None:
    source = '''tool "convert text to lowercase":
  implemented using python

  input:
    text is text

  output:
    text is text

tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text
    ok is boolean

flow "demo":
  let lower is convert text to lowercase:
    text is input.text
  let greet is greeter:
    name is input.name
  return greet
'''
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["tools", "bind", "--auto", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "greeter" in data["missing_bound"]
    bindings_path = tmp_path / ".namel3ss" / "tools.yaml"
    bindings_text = bindings_path.read_text(encoding="utf-8")
    assert '"greeter"' in bindings_text
    assert "convert text to lowercase" not in bindings_text

    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"text": "Hello World", "name": "Ada"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"message": "", "ok": False}
    tool_calls = [event for event in result.traces if isinstance(event, dict) and event.get("type") == "tool_call"]
    assert any(
        event["tool"] == "convert text to lowercase" and event["resolved_source"] == "builtin_pack"
        for event in tool_calls
    )
    assert any(event["tool"] == "greeter" and event["resolved_source"] == "binding" for event in tool_calls)
