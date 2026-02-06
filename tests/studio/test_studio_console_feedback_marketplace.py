from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from namel3ss.studio.api_routes import handle_api_get, handle_api_post
from namel3ss.studio.session import SessionState


SOURCE = (
    'spec is "1.0"\n\n'
    'flow "ask_ai":\n'
    '  return "ok"\n\n'
    'page "home":\n'
    '  button "Ask":\n'
    '    calls flow "ask_ai"\n'
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



def test_console_feedback_marketplace_get_endpoints(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "mlops.yaml").write_text(
        f"registry_url: {(tmp_path / 'registry_ops.json').as_uri()}\nproject_name: demo\n",
        encoding="utf-8",
    )
    for path in [
        "/api/console",
        "/api/feedback",
        "/api/retrain",
        "/api/canary",
        "/api/marketplace",
        "/api/tutorials",
        "/api/playground",
        "/api/versioning",
        "/api/quality",
        "/api/mlops",
        "/api/triggers",
    ]:
        handler = DummyHandler(path=path, app_path=app_path)
        handle_api_get(handler)
        assert handler.status == 200
        assert isinstance(handler.payload, dict)
        assert handler.error is None



def test_console_feedback_marketplace_post_endpoints(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "mlops.yaml").write_text(
        f"registry_url: {(tmp_path / 'registry_ops.json').as_uri()}\nproject_name: demo\n",
        encoding="utf-8",
    )
    post_cases = [
        ("/api/console/validate", b'{"source":"spec is \\\"1.0\\\"\\n\\nflow \\\"ask_ai\\\":\\n  return \\\"ok\\\"\\n"}'),
        ("/api/feedback", b'{"flow_name":"ask_ai","input_text":"hello","rating":"good"}'),
        ("/api/retrain/schedule", b"{}"),
        ("/api/marketplace", b'{"action":"search","query":"demo"}'),
        ("/api/tutorials", b'{"action":"list"}'),
        ("/api/tutorials", b'{"action":"run","slug":"basics","auto":true}'),
        (
            "/api/playground",
            b'{"action":"check","source":"spec is \\"1.0\\"\\n\\nflow \\"demo\\":\\n  return \\"ok\\"\\n"}',
        ),
        ("/api/versioning", b'{"action":"list"}'),
        ("/api/quality", b"{}"),
        (
            "/api/mlops",
            b'{"action":"register_model","name":"base","version":"1.0","artifact_uri":"model://base/1.0","experiment_id":"manual"}',
        ),
        ("/api/triggers", b'{"action":"register","type":"webhook","name":"user_signup","pattern":"/hooks/signup","flow":"ask_ai"}'),
    ]
    for path, body in post_cases:
        handler = DummyHandler(path=path, app_path=app_path, body=body)
        handle_api_post(handler)
        assert handler.status == 200
        assert isinstance(handler.payload, dict)
        assert handler.error is None


def test_mlops_post_returns_400_for_invalid_registry_uri(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "mlops.yaml").write_text(
        "registry_url: file:///tmp/registry_ops.json?bad=1\nproject_name: demo\n",
        encoding="utf-8",
    )
    handler = DummyHandler(
        path="/api/mlops",
        app_path=app_path,
        body=b'{"action":"register_model","name":"base","version":"1.0","artifact_uri":"model://base/1.0","experiment_id":"manual"}',
    )
    handle_api_post(handler)
    assert handler.status == 400
    assert isinstance(handler.payload, dict)
    assert handler.payload.get("ok") is False
    assert handler.error is None
