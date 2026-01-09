from pathlib import Path
import json
import os
import shutil
import sys

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.tools.bindings import write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.python_subprocess import ToolSubprocessResult
from tests.conftest import lower_ir_program
from tests._ci_debug import debug_context


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


def _copy_tool_fixture(tmp_path: Path) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".namel3ss").mkdir()
    shutil.copy(FIXTURES_ROOT / ".namel3ss" / "tools.yaml", project_root / ".namel3ss" / "tools.yaml")
    shutil.copytree(FIXTURES_ROOT / "tools", project_root / "tools")
    return project_root


def test_python_tool_call_success_traces_event(tmp_path: Path):
    project_root = _copy_tool_fixture(tmp_path)
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
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(project_root),
    )
    result = executor.run()
    assert result.last_value == {"message": "Hello Ada", "ok": True}
    tool_events = [event for event in result.traces if isinstance(event, dict) and event.get("type") == "tool_call"]
    assert tool_events
    tool_event = tool_events[0]
    assert tool_event["status"] == "ok"
    assert tool_event["kind"] == "python"
    assert tool_event["purity"] == "impure"
    assert tool_event["runner"] == "local"
    assert tool_event["python_env"] == "system"
    assert tool_event["deps_source"] == "none"
    assert tool_event["python_path"] == sys.executable
    assert tool_event["timeout_ms"] == 10000
    assert isinstance(tool_event["duration_ms"], int)
    assert tool_event["resolved_source"] == "binding"
    assert "input_summary" in tool_event
    assert "output_summary" in tool_event


def test_python_tool_schema_mismatch_error(tmp_path: Path):
    project_root = _copy_tool_fixture(tmp_path)
    source = '''tool "bad_output":
  implemented using python

  input:
    name is text

  output:
    message is text
    ok is boolean

spec is "1.0"

flow "demo":
  let result is bad_output:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(project_root),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    message = str(exc.value).lower()
    assert "output" in message


def test_python_tool_missing_module_error(tmp_path: Path):
    project_root = _copy_tool_fixture(tmp_path)
    source = '''tool "missing":
  implemented using python

  input:
    name is text

  output:
    message is text

spec is "1.0"

flow "demo":
  let result is missing:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(project_root),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    message = str(exc.value)
    if "missing_tool" not in message and os.getenv("CI") == "true":
        tools_yaml = project_root / ".namel3ss" / "tools.yaml"
        missing_block: list[str] = []
        if tools_yaml.exists():
            lines = tools_yaml.read_text(encoding="utf-8").splitlines()
            idx = next((i for i, line in enumerate(lines) if '"missing"' in line), None)
            if idx is not None:
                missing_block = lines[idx : idx + 3]
        print(json.dumps(debug_context("missing_module_error", app_root=project_root), sort_keys=True))
        print(json.dumps({"tools_yaml": str(tools_yaml), "exists": tools_yaml.exists(), "missing_block": missing_block}, sort_keys=True))
        print("error:\n" + message)
    assert "missing_tool" in message
    assert "module" in message.lower()


def test_python_tool_missing_binding_error_includes_guidance(tmp_path: Path) -> None:
    source = '''tool "unbound":
  implemented using python

  input:
    name is text

  output:
    message is text

spec is "1.0"

flow "demo":
  let result is unbound:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    message = str(exc.value)
    assert "n3 tools bind" in message
    assert "n3 tools status" in message


def test_python_tool_uses_venv_python(monkeypatch, tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "sample_tool.py").write_text(
        "def greet(payload):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")

    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    seen = {}
    write_tool_bindings(tmp_path, {"greeter": ToolBinding(kind="python", entry="tools.sample_tool:greet")})

    def fake_run_tool_subprocess(
        *,
        python_path,
        tool_name,
        entry,
        payload,
        app_root,
        timeout_seconds,
        extra_paths=None,
        capability_context=None,
        sandbox=None,
        trace_id=None,
    ):
        seen["python_path"] = python_path
        return ToolSubprocessResult(ok=True, output={"ok": True}, error_type=None, error_message=None)

    monkeypatch.setattr("namel3ss.runtime.tools.runners.local_runner.run_tool_subprocess", fake_run_tool_subprocess)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"ok": True}
    assert seen["python_path"] == venv_python
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["runner"] == "local"
    assert tool_event["python_env"] == "venv"


def test_python_tool_uses_system_python_without_venv(monkeypatch, tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "sample_tool.py").write_text(
        "def greet(payload):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )

    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    seen = {}
    write_tool_bindings(tmp_path, {"greeter": ToolBinding(kind="python", entry="tools.sample_tool:greet")})

    def fake_run_tool_subprocess(
        *,
        python_path,
        tool_name,
        entry,
        payload,
        app_root,
        timeout_seconds,
        extra_paths=None,
        capability_context=None,
        sandbox=None,
        trace_id=None,
    ):
        seen["python_path"] = python_path
        return ToolSubprocessResult(ok=True, output={"ok": True}, error_type=None, error_message=None)

    monkeypatch.setattr("namel3ss.runtime.tools.runners.local_runner.run_tool_subprocess", fake_run_tool_subprocess)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    result = executor.run()
    assert result.last_value == {"ok": True}
    assert str(seen["python_path"]) == sys.executable
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["runner"] == "local"
    assert tool_event["python_env"] == "system"


def test_python_tool_failure_surfaces_error(monkeypatch, tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "sample_tool.py").write_text(
        "def greet(payload):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )

    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    write_tool_bindings(tmp_path, {"greeter": ToolBinding(kind="python", entry="tools.sample_tool:greet")})

    def fake_run_tool_subprocess(
        *,
        python_path,
        tool_name,
        entry,
        payload,
        app_root,
        timeout_seconds,
        extra_paths=None,
        capability_context=None,
        sandbox=None,
        trace_id=None,
    ):
        return ToolSubprocessResult(ok=False, output=None, error_type="ValueError", error_message="boom")

    monkeypatch.setattr("namel3ss.runtime.tools.runners.local_runner.run_tool_subprocess", fake_run_tool_subprocess)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "ValueError" in str(exc.value)


def test_python_tool_invalid_venv_python_path(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "sample_tool.py").write_text(
        "def greet(payload):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )
    venv_path = tmp_path / ".venv"
    venv_path.mkdir()

    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    ok is boolean

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    program = lower_ir_program(source)
    write_tool_bindings(tmp_path, {"greeter": ToolBinding(kind="python", entry="tools.sample_tool:greet")})
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "venv exists but python was not found" in str(exc.value).lower()
