from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.utils.slugify import slugify_text
from tests.conftest import lower_ir_program


class FakeHeaders:
    def __init__(self, items: list[tuple[str, str]]):
        self._items = items

    def items(self):
        return list(self._items)


class FakeResponse:
    def __init__(self, body: str, headers: list[tuple[str, str]], status: int = 200):
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = FakeHeaders(headers)

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _build_executor(tmp_path: Path, source: str, flow_name: str = "demo") -> Executor:
    program = lower_ir_program(source)
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    flow = next(flow for flow in program.flows if flow.name == flow_name)
    schemas = {schema.name: schema for schema in program.records}
    return Executor(
        flow,
        schemas=schemas,
        store=MemoryStore(),
        tools=program.tools,
        functions=program.functions,
        agents=program.agents,
        ai_profiles=program.ais,
        jobs={job.name: job for job in program.jobs},
        job_order=[job.name for job in program.jobs],
        capabilities=program.capabilities,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def test_http_tool_trace_and_output(monkeypatch, tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  http

tool "fetch status":
  implemented using http

  input:
    url is text

  output:
    status is number
    headers is json
    body is text

flow "demo":
  let response is fetch status:
    url is "https://example.com"
  return response
'''

    def fake_urlopen(_req, timeout):
        return FakeResponse(
            "ok",
            [
                ("X-B", "b"),
                ("Content-Type", "text/plain"),
                ("X-A", "a"),
            ],
            status=200,
        )

    monkeypatch.setattr("namel3ss.runtime.backend.http_capability.safe_urlopen", fake_urlopen)

    executor = _build_executor(tmp_path, source)
    result = executor.run()

    assert result.last_value["status"] == 200
    assert result.last_value["body"] == "ok"
    assert result.last_value["headers"] == [
        {"name": "Content-Type", "value": "text/plain"},
        {"name": "X-A", "value": "a"},
        {"name": "X-B", "value": "b"},
    ]

    http_events = [
        event
        for event in result.traces
        if isinstance(event, dict) and event.get("kind") == "http"
    ]
    assert http_events
    event = http_events[-1]
    assert event["input"]["url"] == "https://example.com"
    assert event["output"]["status"] == 200
    assert event["output"]["body"]["type"] == "text"


def test_file_tool_scoped_and_traced(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  files

tool "write note":
  implemented using file

  input:
    operation is text
    path is text
    content is text

  output:
    ok is boolean
    bytes is number

tool "read note":
  implemented using file

  input:
    operation is text
    path is text

  output:
    content is text
    ok is boolean
    bytes is number

flow "demo":
  let write_result is write note:
    operation is "write"
    path is "notes/hello.txt"
    content is "hello"
  let read_result is read note:
    operation is "read"
    path is "notes/hello.txt"
  return read_result
'''
    executor = _build_executor(tmp_path, source)
    result = executor.run()

    assert result.last_value["content"] == "hello"
    assert result.last_value["ok"] is True

    scope = slugify_text("app.ai")
    target = tmp_path / ".namel3ss" / "files" / scope / "notes" / "hello.txt"
    assert target.exists()

    file_events = [
        event
        for event in result.traces
        if isinstance(event, dict) and event.get("kind") == "file"
    ]
    assert file_events
    event = file_events[0]
    assert "notes/hello.txt" in event["input"]["path"]
    assert str(tmp_path) not in event["input"]["path"]


def test_file_tool_rejects_parent_path(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  files

tool "read note":
  implemented using file

  input:
    operation is text
    path is text

  output:
    content is text
    ok is boolean
    bytes is number

flow "demo":
  let read_result is read note:
    operation is "read"
    path is "../secrets.txt"
  return read_result
'''
    executor = _build_executor(tmp_path, source)
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "File path must be relative" in exc.value.message


def test_job_enqueue_order(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  jobs

job "first":
  return "one"

job "second":
  return "two"

flow "demo":
  enqueue job "first"
  enqueue job "second"
  return "ok"
'''
    executor = _build_executor(tmp_path, source)
    result = executor.run()

    events = [
        event
        for event in result.traces
        if isinstance(event, dict) and event.get("type") in {"job_enqueued", "job_started", "job_finished"}
    ]
    ordered = [f"{event['type']}:{event['job']}" for event in events]
    assert ordered == [
        "job_enqueued:first",
        "job_enqueued:second",
        "job_started:first",
        "job_finished:first",
        "job_started:second",
        "job_finished:second",
    ]


def test_job_when_triggers_on_state_change(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  jobs

job "flip" when state.ready is true:
  set state.ready is false

flow "demo":
  set state.ready is true
  return "ok"
'''
    executor = _build_executor(tmp_path, source)
    result = executor.run()

    assert result.state["ready"] is False
    finished = [
        event
        for event in result.traces
        if isinstance(event, dict) and event.get("type") == "job_finished" and event.get("job") == "flip"
    ]
    assert finished
