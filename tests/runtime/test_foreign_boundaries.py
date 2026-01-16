from __future__ import annotations

import time
from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor, execute_program_flow


def _write_tool(tmp_path: Path, filename: str, body: str) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / filename).write_text(body, encoding="utf-8")


def _write_bindings(tmp_path: Path, tool_name: str, entry: str, *, timeout_ms: int | None = None) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir(exist_ok=True)
    lines = [
        "tools:",
        f'  "{tool_name}":',
        '    kind: "python"',
        f'    entry: "{entry}"',
    ]
    if timeout_ms is not None:
        lines.append(f"    timeout_ms: {timeout_ms}")
    (tools_dir / "tools.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_app(tmp_path: Path, source: str) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    return app_path


def test_foreign_call_emits_boundary_traces(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "adder.py",
        "def run(payload):\n"
        "    return payload.get(\"amount\", 0) + 1\n",
    )
    _write_bindings(tmp_path, "adder", "tools.adder:run")
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"

foreign python function "adder"
  input
    amount is number
  output is number

flow "demo"
  call foreign "adder"
    amount is 1
''',
    )
    program, _ = load_program(app_path.as_posix())
    result = execute_program_flow(program, "demo", config=AppConfig())
    boundary = [event for event in result.traces if event.get("type") in {"boundary_start", "boundary_end"}]
    assert [event.get("type") for event in boundary] == ["boundary_start", "boundary_end"]
    assert boundary[0]["language"] == "python"
    assert boundary[0]["function_name"] == "adder"
    assert boundary[0]["policy_mode"] == "default"
    assert boundary[1]["status"] == "ok"
    assert "output_summary" in boundary[1]


def test_foreign_strict_policy_blocks(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "adder.py",
        "def run(payload):\n"
        "    return payload.get(\"amount\", 0) + 1\n",
    )
    _write_bindings(tmp_path, "adder", "tools.adder:run")
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"

foreign python function "adder"
  input
    amount is number
  output is number

flow "demo"
  call foreign "adder"
    amount is 1
''',
    )
    program, _ = load_program(app_path.as_posix())
    config = AppConfig()
    config.foreign.strict = True
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={},
        config=config,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "strict determinism" in str(exc.value)
    boundary = [event for event in executor.traces if event.get("type") in {"boundary_start", "boundary_end"}]
    assert boundary
    assert boundary[-1].get("status") == "blocked"


def test_foreign_network_blocked_by_default(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "fetcher.py",
        "from urllib import request\n\n"
        "def run(payload):\n"
        "    request.urlopen(payload.get(\"url\"))\n"
        "    return True\n",
    )
    _write_bindings(tmp_path, "fetcher", "tools.fetcher:run")
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"

foreign python function "fetcher"
  input
    url is text
  output is boolean

flow "demo"
  call foreign "fetcher"
    url is "https://example.com"
''',
    )
    program, _ = load_program(app_path.as_posix())
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={},
        config=AppConfig(),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    for event in executor.traces:
        if event.get("type") == "capability_check" and event.get("capability") == "network":
            assert event.get("allowed") is False
            return
    raise AssertionError("Missing network capability_check")


def test_foreign_output_type_mismatch(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "bad_output.py",
        "def run(payload):\n"
        "    return \"oops\"\n",
    )
    _write_bindings(tmp_path, "bad output", "tools.bad_output:run")
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"

foreign python function "bad output"
  input
    amount is number
  output is number

flow "demo"
  call foreign "bad output"
    amount is 1
''',
    )
    program, _ = load_program(app_path.as_posix())
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={},
        config=AppConfig(),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "Foreign output" in str(exc.value)


def test_foreign_timeout_enforced(tmp_path: Path) -> None:
    _write_tool(
        tmp_path,
        "slow.py",
        "import time\n\n"
        "def run(payload):\n"
        "    time.sleep(2)\n"
        "    return 1\n",
    )
    _write_bindings(tmp_path, "slow", "tools.slow:run", timeout_ms=1000)
    app_path = _write_app(
        tmp_path,
        '''
spec is "1.0"

foreign python function "slow"
  input
    wait is number
  output is number

flow "demo"
  call foreign "slow"
    wait is 1
''',
    )
    program, _ = load_program(app_path.as_posix())
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={},
        config=AppConfig(),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    start = time.monotonic()
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    elapsed = time.monotonic() - start
    assert elapsed < 5
    assert "timed out" in str(exc.value).lower()
