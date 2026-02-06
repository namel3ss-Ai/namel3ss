from __future__ import annotations

import io
from dataclasses import dataclass
from types import SimpleNamespace
from pathlib import Path

from namel3ss.studio.api_routes import handle_api_get, handle_api_post
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
        self.wfile = io.BytesIO()
        self.payload = None
        self.status = None
        self.error = None
        self.response_headers = {}
        self.server = SimpleNamespace(app_path=str(self.app_path), session_state=SessionState())

    def _read_source(self) -> str:
        return self.app_path.read_text(encoding="utf-8")

    def _get_session(self) -> SessionState:
        return self.server.session_state

    def _respond_json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.status = status
        if headers:
            self.response_headers.update(headers)

    def send_response(self, code: int) -> None:
        self.status = code

    def send_header(self, key: str, value: str) -> None:
        self.response_headers[key] = value

    def end_headers(self) -> None:
        return

    def send_error(self, code: int) -> None:
        self.error = code


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def test_kept_get_endpoints_return_ok(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    for path in [
        "/api/summary",
        "/api/ui",
        "/api/actions",
        "/api/lint",
        "/api/formulas",
        "/api/graph",
        "/api/exports",
        "/api/tools",
        "/api/secrets",
        "/api/providers",
        "/api/dependencies",
        "/api/diagnostics",
        "/api/version",
        "/api/why",
        "/api/agents",
        "/api/security",
    ]:
        handler = DummyHandler(path=path, app_path=app_path)
        handle_api_get(handler)
        assert handler.status == 200
        assert isinstance(handler.payload, dict)
        assert handler.error is None


def test_action_post_still_executes(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    body = b'{"id":"page.home.button.run","payload":{}}'
    handler = DummyHandler(path="/api/action", app_path=app_path, body=body)
    handle_api_post(handler)
    assert handler.status == 200
    assert handler.payload["ok"] is True


def test_action_stream_post_returns_sse(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    body = b'{"id":"page.home.button.run","payload":{}}'
    handler = DummyHandler(path="/api/action/stream", app_path=app_path, body=body)
    handle_api_post(handler)
    assert handler.status == 200
    assert handler.payload is None
    assert handler.response_headers.get("Content-Type") == "text/event-stream; charset=utf-8"
    data = handler.wfile.getvalue().decode("utf-8")
    assert "event: return" in data


def test_agent_memory_pack_post_returns_ok(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    body = b'{"default_pack":"auto","agent_overrides":{}}'
    handler = DummyHandler(path="/api/agent/memory_packs", app_path=app_path, body=body)
    handle_api_post(handler)
    assert handler.status == 200
    assert handler.payload["ok"] is True


def test_provider_settings_post_returns_ok(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    body = b'{"action":"save","settings":{"huggingface":{"default_model":"huggingface:bert-base-uncased"}}}'
    handler = DummyHandler(path="/api/providers", app_path=app_path, body=body)
    handle_api_post(handler)
    assert handler.status == 200
    assert handler.payload["ok"] is True


def test_removed_get_endpoints_404(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    removed = [
        "/api/trust/summary",
        "/api/trust/proof",
        "/api/trust/secrets",
        "/api/trust/observe?limit=10",
        "/api/trust/explain",
        "/api/pkg/search?q=demo",
        "/api/pkg/info?name=demo",
        "/api/registry/status",
        "/api/packs",
        "/api/data/summary",
        "/api/audit?limit=10",
        "/api/memory/agreements",
        "/api/memory/rules",
        "/api/memory/packs",
        "/api/memory/handoff",
    ]
    for path in removed:
        handler = DummyHandler(path=path, app_path=app_path)
        handle_api_get(handler)
        assert handler.error == 404


def test_removed_post_endpoints_404(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    removed = [
        "/api/edit",
        "/api/tool-wizard",
        "/api/tools/auto-bind",
        "/api/packs/add",
        "/api/packs/verify",
        "/api/packs/enable",
        "/api/packs/disable",
        "/api/packs/install",
        "/api/registry/add_bundle",
        "/api/discover",
        "/api/security/override",
        "/api/security/sandbox",
        "/api/trust/verify",
        "/api/editor/diagnose",
        "/api/editor/fix",
        "/api/editor/rename",
        "/api/editor/apply",
        "/api/memory/agreements/approve",
        "/api/memory/agreements/reject",
        "/api/memory/rules/propose",
        "/api/memory/handoff/create",
        "/api/memory/handoff/apply",
        "/api/memory/handoff/reject",
        "/api/theme",
        "/api/reset",
    ]
    for path in removed:
        handler = DummyHandler(path=path, app_path=app_path, body=b"{}")
        handle_api_post(handler)
        assert handler.error == 404
