from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


def _run_blocked(source: str, config: AppConfig, tmp_path: Path) -> list[dict[str, object]]:
    program = lower_ir_program(source)
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
    return [event for event in executor.traces if isinstance(event, dict)]


def _expect_block(traces: list[dict[str, object]], capability: str) -> dict[str, object]:
    for event in traces:
        if event.get("type") == "capability_check" and event.get("capability") == capability:
            assert event.get("allowed") is False
            return event
    raise AssertionError(f"Missing capability_check for {capability}")


def test_builtin_pack_blocks_network(tmp_path: Path) -> None:
    source = '''tool "get json from web":
  implemented using python

  input:
    url is text

  output:
    status is number
    headers is json
    data is json

flow "demo":
  let response is get json from web:
    url is "https://example.com/data"
  return response
'''
    config = AppConfig()
    config.capability_overrides = {"get json from web": {"no_network": True}}
    traces = _run_blocked(source, config, tmp_path)
    _expect_block(traces, "network")


def test_builtin_pack_blocks_filesystem_write(tmp_path: Path) -> None:
    source = '''tool "write text file":
  implemented using python

  input:
    path is text
    text is text

  output:
    ok is boolean
    path is text

flow "demo":
  let result is write text file:
    path is "blocked.txt"
    text is "nope"
  return result
'''
    config = AppConfig()
    config.capability_overrides = {"write text file": {"no_filesystem_write": True}}
    traces = _run_blocked(source, config, tmp_path)
    _expect_block(traces, "filesystem_write")
