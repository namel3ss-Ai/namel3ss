from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.runners import registry as runner_registry
from namel3ss.runtime.tools.runners.base import ToolRunnerResult
from namel3ss.runtime.tools.runners.local_runner import LocalRunner
from tests.conftest import lower_ir_program


class StubRunner:
    def __init__(self, name: str, metadata: dict[str, object]) -> None:
        self.name = name
        self._metadata = dict(metadata)

    def execute(self, request):  # type: ignore[override]
        metadata = dict(self._metadata)
        metadata.setdefault("runner", self.name)
        return ToolRunnerResult(
            ok=True,
            output={"result": {"ok": True}},
            error_type=None,
            error_message=None,
            metadata=metadata,
        )


def _patch_runners(monkeypatch: pytest.MonkeyPatch) -> None:
    runners = dict(runner_registry._RUNNERS)
    runners["local"] = runners.get("local", LocalRunner())
    runners["service"] = StubRunner(
        "service",
        {
            "service_url": "http://service.local/tools",
            "protocol_version": 1,
        },
    )
    runners["container"] = StubRunner(
        "container",
        {
            "container_runtime": "docker",
            "protocol_version": 1,
        },
    )
    monkeypatch.setattr(runner_registry, "_RUNNERS", runners)


def _write_local_tool(app_root: Path) -> None:
    tools_dir = app_root / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "local_tool.py").write_text(
        "def run(payload):\n"
        "    return {\"result\": payload}\n",
        encoding="utf-8",
    )


def _write_bindings(app_root: Path) -> None:
    bindings = {
        "local echo": ToolBinding(kind="python", entry="tools.local_tool:run"),
        "service echo": ToolBinding(
            kind="python",
            entry="tools.service_tool:run",
            runner="service",
            url="http://service.local/tools",
        ),
        "container echo": ToolBinding(
            kind="python",
            entry="tools.container_tool:run",
            runner="container",
            image="ghcr.io/namel3ss/tools:latest",
            command=["python", "-m", "namel3ss_tools.runner"],
        ),
    }
    write_tool_bindings(app_root, bindings)


def _assert_keys(event: dict[str, object], keys: set[str]) -> None:
    missing = [key for key in keys if key not in event]
    assert not missing, f"Missing keys {missing} for tool {event.get('tool_name')}"


def test_tool_trace_schema_v1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_runners(monkeypatch)
    _write_local_tool(tmp_path)
    _write_bindings(tmp_path)

    source = '''tool "local echo":
  implemented using python

  input:
    payload is json

  output:
    result is json

tool "service echo":
  implemented using python

  input:
    payload is json

  output:
    result is json

tool "container echo":
  implemented using python

  input:
    payload is json

  output:
    result is json

tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

spec is "1.0"

flow "demo":
  let local_result is local echo:
    payload is input.payload
  let service_result is service echo:
    payload is input.payload
  let container_result is container echo:
    payload is input.payload
  let pack_result is slugify text:
    text is input.text
  return pack_result
'''

    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}, "text": "Hello World"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    tool_events = [event for event in result.traces if isinstance(event, dict) and event.get("type") == "tool_call"]
    events = {event.get("tool_name"): event for event in tool_events}

    expected_names = {"local echo", "service echo", "container echo", "slugify text"}
    assert expected_names.issubset(events.keys())

    base_keys = {
        "type",
        "tool_name",
        "resolved_source",
        "runner",
        "status",
        "duration_ms",
        "timeout_ms",
        "protocol_version",
    }
    for name in expected_names:
        _assert_keys(events[name], base_keys)

    local_event = events["local echo"]
    assert local_event["resolved_source"] == "binding"
    assert local_event["runner"] == "local"
    _assert_keys(local_event, {"entry", "python_env", "python_path", "deps_source"})

    service_event = events["service echo"]
    assert service_event["resolved_source"] == "binding"
    assert service_event["runner"] == "service"
    _assert_keys(service_event, {"entry", "service_url"})

    container_event = events["container echo"]
    assert container_event["resolved_source"] == "binding"
    assert container_event["runner"] == "container"
    _assert_keys(container_event, {"entry", "container_runtime", "image", "command"})

    pack_event = events["slugify text"]
    assert pack_event["resolved_source"] == "builtin_pack"
    _assert_keys(pack_event, {"pack_id", "pack_version"})
