from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIToolCallResponse
from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor.api import execute_program_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "do thing":
  implemented using python
  input:
    name is text
  output:
    result is text

ai "assistant":
  provider is "mock"
  model is "mock"
  tools:
    expose "do thing"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


def test_tool_boundary_wrapped(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    program = lower_ir_program(SOURCE)
    setattr(program, "project_root", tmp_path)
    setattr(program, "app_path", app_path)
    mock_provider = MockProvider(tool_call_sequence=[AIToolCallResponse(tool_name="do thing", args={})])

    with pytest.raises(Namel3ssError) as excinfo:
        execute_program_flow(program, "demo", ai_provider=mock_provider)

    message = str(excinfo.value)
    assert "error:" in message.lower()
    assert "error id" in message.lower()

    payload = json.loads((tmp_path / ".namel3ss" / "errors" / "last.json").read_text(encoding="utf-8"))
    assert payload["error"]["boundary"] == "tools"
    assert payload["error"]["error_id"].startswith("E-")
