from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from namel3ss.governance.audit import record_audit_entry
from namel3ss.studio.api_routes import handle_api_get, handle_api_post
from namel3ss.studio.session import SessionState


SOURCE = (
    'spec is "1.0"\n\n'
    'flow "demo":\n'
    '  return "ok"\n'
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
        self.server = SimpleNamespace(app_path=str(self.app_path), session_state=SessionState())

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


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def test_security_get_endpoint_returns_payload(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    handler = DummyHandler(path="/api/security", app_path=app_path)
    handle_api_get(handler)
    assert handler.status in {200, 400}
    assert isinstance(handler.payload, dict)
    assert "configs" in handler.payload
    assert "requires" in handler.payload
    assert handler.error is None


def test_audit_logs_get_endpoint_supports_pagination(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    record_audit_entry(
        project_root=app_path.parent,
        app_path=app_path,
        user="alice",
        action="secret_add",
        resource="db_password",
        status="success",
        details={"token": "redacted"},
    )
    record_audit_entry(
        project_root=app_path.parent,
        app_path=app_path,
        user="bob",
        action="secret_remove",
        resource="db_password",
        status="success",
        details={},
    )

    handler = DummyHandler(path="/api/audit/logs?limit=1&offset=0", app_path=app_path)
    handle_api_get(handler)
    assert handler.status == 200
    assert isinstance(handler.payload, dict)
    assert handler.payload["ok"] is True
    assert handler.payload["count"] == 1
    assert handler.payload["total_count"] >= 2
    assert len(handler.payload["entries"]) == 1
    assert handler.error is None


def test_auth_alias_post_endpoints_do_not_404(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)

    login_handler = DummyHandler(path="/api/auth/login", app_path=app_path, body=b"{}")
    handle_api_post(login_handler)
    assert login_handler.error is None
    assert login_handler.status in {200, 400}
    assert isinstance(login_handler.payload, dict)

    logout_handler = DummyHandler(path="/api/auth/logout", app_path=app_path, body=b"{}")
    handle_api_post(logout_handler)
    assert logout_handler.error is None
    assert logout_handler.status in {200, 400, 401}
    assert isinstance(logout_handler.payload, dict)
