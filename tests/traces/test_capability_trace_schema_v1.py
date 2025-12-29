from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


def test_capability_check_trace_schema_v1(tmp_path: Path) -> None:
    source = '''tool "get json from web":
  implemented using python

  input:
    url is text

  output:
    status is number
    headers is json
    data is json

spec is "1.0"

flow "demo":
  let response is get json from web:
    url is "https://example.com/data"
  return response
'''
    program = lower_ir_program(source)
    config = AppConfig()
    config.capability_overrides = {"get json from web": {"no_network": True}}
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
    checks = [event for event in executor.traces if isinstance(event, dict) and event.get("type") == "capability_check"]
    assert checks, "Expected a capability_check trace event"
    event = checks[0]
    required = {
        "type",
        "tool_name",
        "resolved_source",
        "runner",
        "capability",
        "allowed",
        "guarantee_source",
        "reason",
        "protocol_version",
    }
    missing = [key for key in required if key not in event]
    assert not missing, f"Missing capability_check keys: {missing}"
    assert event["capability"] == "network"
    assert event["allowed"] is False
