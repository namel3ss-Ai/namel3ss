from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.router.streaming import should_stream_response
from tests.conftest import run_flow


def test_async_await_collects_result_and_yields_are_ordered() -> None:
    source = '''spec is "1.0"

define function "calc":
  input:
    value is number
  output:
    total is number
  return map:
    "total" is value + 1

flow "demo":
  let future_task is async call function "calc":
    value is 2
  yield "starting"
  await future_task
  yield future_task.total
  return future_task.total
'''
    result = run_flow(source)
    assert result.last_value == Decimal("3")
    assert [item.get("sequence") for item in result.yield_messages] == [1, 2]
    assert [item.get("output") for item in result.yield_messages] == ["starting", Decimal("3")]


def test_route_dispatch_streams_yield_messages_as_sse(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "stream_flow":\n'
        '  yield "starting"\n'
        '  return "done"\n\n'
        'route "stream_route":\n'
        '  path is "/api/stream"\n'
        '  method is "GET"\n'
        "  request:\n"
        "    payload is text\n"
        "  response:\n"
        "    status is text\n"
        '  flow is "stream_flow"\n',
        encoding="utf-8",
    )
    program, _ = load_program(app.as_posix())
    registry = RouteRegistry()
    registry.update(program.routes)
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/stream",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
    )
    assert result is not None
    assert result.status == 200
    assert result.payload is None
    assert result.body is not None
    assert result.content_type == "text/event-stream; charset=utf-8"
    body = result.body.decode("utf-8")
    assert "event: yield" in body
    assert "event: return" in body
    assert '"status":"done"' in body


def test_ai_stream_events_require_explicit_stream_request() -> None:
    events = [
        {
            "flow_name": "demo",
            "output": "chunk",
            "sequence": 1,
            "event_type": "token",
            "stream_channel": "ai",
        }
    ]
    assert should_stream_response({}, {}, events) is False
    assert should_stream_response({"stream": "true"}, {}, events) is True
