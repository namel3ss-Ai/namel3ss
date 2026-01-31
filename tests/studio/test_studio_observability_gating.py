from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from namel3ss.observability.log_store import logs_path
from namel3ss.studio.api_routes import handle_api_get
from namel3ss.studio.session import SessionState


SOURCE = (
    'spec is "1.0"\n\n'
    'flow "demo":\n'
    '  return "ok"\n\n'
    'page "home":\n'
    '  button "Run":\n'
    '    calls flow "demo"\n'
)


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
        self.payload = payload
        self.status = status

    def send_error(self, code: int) -> None:
        self.error = code


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def _write_logs(tmp_path: Path, app_path: Path) -> None:
    path = logs_path(tmp_path, app_path)
    assert path is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"id": "log:0001", "level": "info", "message": "ok"}]
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def test_studio_observability_disabled_is_noop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("N3_OBSERVABILITY", raising=False)
    app_path = _write_app(tmp_path)
    _write_logs(tmp_path, app_path)
    handler = DummyHandler(path="/api/logs", app_path=app_path)
    handle_api_get(handler)
    assert handler.status == 200
    assert handler.payload.get("logs") == []
    assert handler.payload.get("count") == 0


def test_studio_observability_enabled_surfaces(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("N3_OBSERVABILITY", "1")
    app_path = _write_app(tmp_path)
    _write_logs(tmp_path, app_path)
    handler = DummyHandler(path="/api/logs", app_path=app_path)
    handle_api_get(handler)
    assert handler.status == 200
    assert handler.payload.get("count") == 1
    assert handler.payload.get("logs")
