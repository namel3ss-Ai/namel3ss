from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


class ToolServiceHandler(BaseHTTPRequestHandler):
    response_payload: dict = {"ok": True, "result": {}}
    last_request: dict | None = None

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence
        pass

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        ToolServiceHandler.last_request = json.loads(raw.decode("utf-8"))
        data = json.dumps(ToolServiceHandler.response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _start_tool_server(payload: dict) -> tuple[HTTPServer, threading.Thread, str]:
    ToolServiceHandler.response_payload = payload
    ToolServiceHandler.last_request = None
    server = HTTPServer(("127.0.0.1", 0), ToolServiceHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/tools"
    return server, thread, url


def _write_service_binding(tmp_path: Path, url: str) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    runner: "service"\n'
        f'    url: "{url}"\n',
        encoding="utf-8",
    )


def test_service_runner_success(tmp_path: Path) -> None:
    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text
    ok is boolean

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    server, thread, url = _start_tool_server({"ok": True, "result": {"message": "Hello Ada", "ok": True}})
    try:
        _write_service_binding(tmp_path, url)
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
        event = next(event for event in result.traces if event.get("type") == "tool_call")
        assert event["runner"] == "service"
        assert event["service_url"] == url
        request = ToolServiceHandler.last_request or {}
        assert request.get("tool_name") == "greeter"
        assert request.get("protocol_version") == 1
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_service_runner_error(tmp_path: Path) -> None:
    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    server, thread, url = _start_tool_server({"ok": False, "error": {"type": "ValueError", "message": "boom"}})
    try:
        _write_service_binding(tmp_path, url)
        program = lower_ir_program(source)
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
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_service_runner_timeout(monkeypatch, tmp_path: Path) -> None:
    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''
    _write_service_binding(tmp_path, "http://127.0.0.1:8787/tools")

    def fake_urlopen(*_args, **_kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr("namel3ss.runtime.tools.runners.service_runner.urlopen", fake_urlopen)
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "Tool service request failed" in str(exc.value)
