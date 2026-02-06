from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from namel3ss.observability.trace_runs import write_trace_run
from namel3ss.studio.api_routes import handle_api_get
from namel3ss.studio.session import SessionState


SOURCE = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'


@dataclass
class DummyHandler:
    path: str
    app_path: Path
    body: bytes | None = None

    def __post_init__(self) -> None:
        self.headers = {"Content-Length": str(len(self.body or b""))}
        self.rfile = io.BytesIO(self.body or b"")
        self.payload = None
        self.status = None
        self.error = None
        self.server = SimpleNamespace(
            app_path=str(self.app_path),
            project_root=str(self.app_path.parent),
            session_state=SessionState(),
        )

    def _read_source(self) -> str:
        return self.app_path.read_text(encoding="utf-8")

    def _get_session(self) -> SessionState:
        return self.server.session_state

    def _respond_json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        _ = headers
        self.payload = payload
        self.status = status

    def send_error(self, code: int) -> None:
        self.error = code


def test_studio_trace_run_endpoints(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    summary = write_trace_run(
        project_root=tmp_path,
        app_path=app,
        flow_name="demo",
        steps=[
            {"id": "step:0001", "kind": "flow_start", "what": "start", "data": {"input": {"x": 1}}},
            {"id": "step:0002", "kind": "flow_end", "what": "end", "data": {"output": {"ok": True}}},
        ],
    )
    assert summary is not None
    run_id = str(summary["run_id"])

    runs_handler = DummyHandler(path="/api/traces/runs", app_path=app)
    handle_api_get(runs_handler)
    assert runs_handler.status == 200
    assert runs_handler.payload["ok"] is True
    assert runs_handler.payload["count"] == 1

    latest_handler = DummyHandler(path="/api/traces/latest", app_path=app)
    handle_api_get(latest_handler)
    assert latest_handler.status == 200
    assert latest_handler.payload["ok"] is True
    assert latest_handler.payload["run_id"] == run_id
    assert latest_handler.payload["count"] == 2

    run_handler = DummyHandler(path=f"/api/traces/{run_id}", app_path=app)
    handle_api_get(run_handler)
    assert run_handler.status == 200
    assert run_handler.payload["ok"] is True
    assert run_handler.payload["run_id"] == run_id
    assert run_handler.payload["count"] == 2
