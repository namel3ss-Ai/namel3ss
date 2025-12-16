from __future__ import annotations

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.studio.api import (
    apply_edit,
    execute_action,
    get_actions_payload,
    get_lint_payload,
    get_summary_payload,
    get_ui_payload,
)
from namel3ss.studio.session import SessionState


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence
        pass

    def _read_source(self) -> str:
        path = Path(self.server.app_path)  # type: ignore[attr-defined]
        return path.read_text(encoding="utf-8")

    def _get_session(self) -> SessionState:
        return self.server.session_state  # type: ignore[attr-defined]

    def _respond_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self.handle_api()
            return
        self.handle_static()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self.handle_api_post()
            return
        self.send_error(404)

    def handle_static(self) -> None:
        web_root = Path(__file__).parent / "web"
        if self.path in {"/", "/index.html"}:
            file_path = web_root / "index.html"
        else:
            file_path = web_root / self.path.lstrip("/")
        if not file_path.exists():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        content_type = "text/html"
        if file_path.suffix == ".js":
            content_type = "application/javascript"
        if file_path.suffix == ".css":
            content_type = "text/css"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_api(self) -> None:
        try:
            source = self._read_source()
        except Exception as err:  # pragma: no cover - IO error edge
            payload = {"ok": False, "error": f"Cannot read source: {err}"}
            self._respond_json(payload, status=500)
            return
        if self.path == "/api/summary":
            payload = get_summary_payload(source, self.server.app_path)  # type: ignore[attr-defined]
            status = 200 if payload.get("ok") else 400
            self._respond_json(payload, status=status)
            return
        if self.path == "/api/ui":
            payload = get_ui_payload(source, self._get_session())
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if self.path == "/api/actions":
            payload = get_actions_payload(source)
            status = 200 if payload.get("ok") else 400
            self._respond_json(payload, status=status)
            return
        if self.path == "/api/lint":
            payload = get_lint_payload(source)
            self._respond_json(payload, status=200)
            return
        self.send_error(404)

    def handle_api_post(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._respond_json({"ok": False, "error": "Invalid JSON body"}, status=400)
            return
        try:
            source = self._read_source()
        except Exception as err:  # pragma: no cover
            payload = {"ok": False, "error": f"Cannot read source: {err}"}
            self._respond_json(payload, status=500)
            return
        if self.path == "/api/edit":
            if not isinstance(body, dict):
                self._respond_json({"ok": False, "error": "Body must be a JSON object"}, status=400)
                return
            op = body.get("op")
            target = body.get("target")
            value = body.get("value", "")
            if not isinstance(op, str):
                self._respond_json({"ok": False, "error": "Edit op is required"}, status=400)
                return
            if not isinstance(target, dict):
                self._respond_json({"ok": False, "error": "Edit target is required"}, status=400)
                return
            if not isinstance(value, str):
                self._respond_json({"ok": False, "error": "Edit value must be a string"}, status=400)
                return
            try:
                resp = apply_edit(self.server.app_path, op, target, value, self._get_session())  # type: ignore[attr-defined]
                self._respond_json(resp, status=200)
                return
            except Namel3ssError as err:
                self._respond_json({"ok": False, "error": format_error(err, source)}, status=400)
                return
        if self.path == "/api/action":
            if not isinstance(body, dict):
                self._respond_json({"ok": False, "error": "Body must be a JSON object"}, status=400)
                return
            action_id = body.get("id")
            payload = body.get("payload") or {}
            if not isinstance(action_id, str):
                self._respond_json({"ok": False, "error": "Action id is required"}, status=400)
                return
            if not isinstance(payload, dict):
                self._respond_json({"ok": False, "error": "Payload must be an object"}, status=400)
                return
            try:
                resp = execute_action(source, self._get_session(), action_id, payload)
                status = 200 if resp.get("ok", True) else 200
                self._respond_json(resp, status=status)
                return
            except Namel3ssError as err:
                self._respond_json({"ok": False, "error": format_error(err, source)}, status=400)
                return
        if self.path == "/api/reset":
            self.server.session_state = SessionState()  # type: ignore[attr-defined]
            self._respond_json({"ok": True}, status=200)
            return
        self.send_error(404)


def start_server(app_path: str, port: int) -> None:
    handler = StudioRequestHandler
    server = HTTPServer(("127.0.0.1", port), handler)
    server.app_path = app_path  # type: ignore[attr-defined]
    server.session_state = SessionState()  # type: ignore[attr-defined]
    print(f"Studio: http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    finally:
        server.server_close()
