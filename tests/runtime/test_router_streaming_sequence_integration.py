from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry


def test_dispatch_route_stream_body_respects_event_order_contract(tmp_path: Path) -> None:
    program = _load_stream_program(tmp_path)
    registry = RouteRegistry()
    registry.update(program.routes)

    def fake_flow_executor(**kwargs):
        return SimpleNamespace(
            last_value={"status": "done"},
            yield_messages=[
                {
                    "event_type": "finish",
                    "flow_name": "assistant.reply",
                    "output": "done",
                    "sequence": 3,
                    "stream_channel": "ai",
                },
                {
                    "event_type": "chat.thread.save",
                    "flow_name": "chat.threads",
                    "output": {"thread_id": "thread.main"},
                    "sequence": 2,
                    "stream_channel": "chat",
                },
                {
                    "event_type": "yield",
                    "flow_name": "stream_flow",
                    "output": {"step": "start"},
                    "sequence": 1,
                },
                {
                    "event_type": "token",
                    "flow_name": "assistant.reply",
                    "output": "d",
                    "sequence": 3,
                    "stream_channel": "ai",
                },
                {
                    "event_type": "progress",
                    "flow_name": "assistant.reply",
                    "output": None,
                    "sequence": 3,
                    "stream_channel": "ai",
                },
                {
                    "event_type": "chat.thread.list",
                    "flow_name": "chat.threads",
                    "output": {"thread_count": 1},
                    "sequence": 2,
                    "stream_channel": "chat",
                },
            ],
        )

    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/stream?stream=true",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=None,
        flow_executor=fake_flow_executor,
    )

    assert result is not None
    assert result.status == 200
    assert result.content_type == "text/event-stream; charset=utf-8"
    assert result.body is not None
    text = result.body.decode("utf-8")
    events = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("event: ")]
    assert events == [
        "yield",
        "chat.thread.list",
        "chat.thread.save",
        "progress",
        "token",
        "finish",
        "return",
    ]


def _load_stream_program(tmp_path: Path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "stream_flow":\n'
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
    return program
