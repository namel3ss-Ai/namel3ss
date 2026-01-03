from __future__ import annotations

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.resources import studio_web_root
from namel3ss.runtime.storage.factory import create_store
from namel3ss.studio.api_routes import handle_api_get, handle_api_post
from namel3ss.studio.session import SessionState
from namel3ss.utils.json_tools import dumps as json_dumps


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence
        pass

    def _read_source(self) -> str:
        path = self.server.app_path  # type: ignore[attr-defined]
        return Path(path).read_text(encoding="utf-8")

    def _get_session(self) -> SessionState:
        return self.server.session_state  # type: ignore[attr-defined]

    def _respond_json(self, payload: dict, status: int = 200) -> None:
        data = json_dumps(to_json_safe(payload)).encode("utf-8")
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
        web_root = studio_web_root()
        parsed = urlparse(self.path)
        path_only = parsed.path
        if path_only in {"/", "/index.html"}:
            file_path = web_root / "index.html"
        else:
            file_path = web_root / path_only.lstrip("/")
        if not file_path.exists():
            file_path = _resolve_repo_static(path_only, file_path)
        if not file_path.exists():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        content_type = "text/html"
        if file_path.suffix == ".js":
            content_type = "application/javascript"
        if file_path.suffix == ".css":
            content_type = "text/css"
        if file_path.suffix == ".svg":
            content_type = "image/svg+xml"
        if file_path.suffix == ".json":
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_api(self) -> None:
        handle_api_get(self)

    def handle_api_post(self) -> None:
        handle_api_post(self)


def _resolve_repo_static(path_only: str, fallback: Path) -> Path:
    if path_only.startswith("/docs/") or path_only.startswith("/examples/"):
        repo_root = Path(__file__).resolve().parents[3]
        candidate = repo_root / path_only.lstrip("/")
        return candidate if candidate.exists() else fallback
    return fallback


def start_server(app_path: str | Path, port: int) -> None:
    app_file = require_app_path(app_path)
    handler = StudioRequestHandler
    server = HTTPServer(("127.0.0.1", port), handler)
    server.app_path = app_file  # type: ignore[attr-defined]
    server.project_root = app_file.parent  # type: ignore[attr-defined]
    server.session_state = build_session_state(app_file)  # type: ignore[attr-defined]
    print(f"Studio: http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def require_app_path(app_path: str | Path | None) -> Path:
    if not app_path:
        raise Namel3ssError(
            build_guidance_message(
                what="Studio needs an app file path to resolve tools/ bindings.",
                why="tools.yaml and tools/ require a project root.",
                fix="Run Studio from the folder that contains app.ai or pass the path explicitly.",
                example="cd <project-root> && n3 studio app.ai",
            )
        )
    path = Path(app_path)
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"App file not found: {path.as_posix()}.",
                why="The path does not point to an existing .ai file.",
                fix="Run Studio from the folder that contains app.ai or pass the path explicitly.",
                example="cd <project-root> && n3 studio app.ai",
            )
        )
    return path.resolve()


def build_session_state(app_path: Path) -> SessionState:
    config = load_config(app_path=app_path, root=app_path.parent)
    store = create_store(config=config)
    return SessionState(store=store)


def to_json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {to_json_safe_key(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, set):
        return [to_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    return value


def to_json_safe_key(value: Any) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


__all__ = [
    "StudioRequestHandler",
    "start_server",
    "require_app_path",
    "build_session_state",
    "to_json_safe",
]
