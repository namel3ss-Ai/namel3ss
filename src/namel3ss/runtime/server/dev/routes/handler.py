from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.server.dev.state import BrowserAppState
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry

from . import answer_explain, core, documents, health, ingestion, packs, studio


class BrowserRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        raw_path = self.path
        path = urlparse(raw_path).path
        if path.startswith("/api/"):
            self._handle_api_get(path, raw_path)
            return
        if self._dispatch_dynamic_route():
            return
        if core.handle_static(self, path):
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/action":
            body = self._read_json_body()
            if body is None:
                payload = build_error_payload("Invalid JSON body.", kind="engine")
                self._respond_json(payload, status=400)
                return
            self._handle_action_post(body)
            return
        if path == "/api/login":
            body = self._read_json_body()
            if body is None:
                payload = build_error_payload("Invalid JSON body.", kind="authentication")
                self._respond_json(payload, status=400)
                return
            payload, status, headers = studio.handle_login_post(self, body)
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/logout":
            payload, status, headers = studio.handle_logout_post(self)
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/upload":
            response, status = ingestion.handle_upload_post(self, parsed.query)
            self._respond_json(response, status=status)
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _handle_api_get(self, path: str, raw_path: str) -> None:
        if answer_explain.handle_answer_explain_get(self, path):
            return
        if studio.handle_session_get(self, path):
            return
        if studio.handle_ui_get(self, path):
            return
        if studio.handle_state_get(self, path):
            return
        if studio.handle_data_status_get(self, path):
            return
        if studio.handle_migrations_status_get(self, path):
            return
        if studio.handle_migrations_plan_get(self, path):
            return
        if ingestion.handle_uploads_get(self, path):
            return
        if documents.handle_documents_get(self, raw_path):
            return
        if core.handle_observability_get(self, path):
            return
        if studio.handle_build_get(self, path):
            return
        if studio.handle_deploy_get(self, path):
            return
        if health.handle_dev_status_get(self, path):
            return
        if health.handle_health_get(self, path):
            return
        if packs.handle_get(self, path):
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _handle_action_post(self, body: dict) -> None:
        studio.handle_action_post(self, body)

    def _read_json_body(self) -> dict | None:
        return core.read_json_body(self)

    def _respond_json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        core.respond_json(self, payload, status=status, headers=headers)

    def _dispatch_dynamic_route(self) -> bool:
        state = self._state()
        state._refresh_if_needed()
        if state.error_payload:
            self._respond_json(state.error_payload, status=400)
            return True
        program = state.program
        if program is None:
            self._respond_json(build_error_payload("Program not loaded.", kind="engine"), status=500)
            return True
        registry = getattr(self.server, "route_registry", None)  # type: ignore[attr-defined]
        if registry is None:
            registry = RouteRegistry()
            self.server.route_registry = registry  # type: ignore[attr-defined]
        refresh_routes(program=program, registry=registry, revision=state.revision, logger=print)
        config = load_config(app_path=state.app_path)
        store = state.session.ensure_store(config)
        result = dispatch_route(
            registry=registry,
            method=self.command,
            raw_path=self.path,
            headers=dict(self.headers.items()),
            rfile=self.rfile,
            program=program,
            identity=None,
            auth_context=None,
            store=store,
        )
        if result is None:
            return False
        if result.body is not None:
            core.respond_bytes(
                self,
                result.body,
                status=result.status,
                content_type=result.content_type or "application/octet-stream",
                headers=result.headers,
            )
            return True
        self._respond_json(result.payload or {}, status=result.status, headers=result.headers)
        return True

    def _state(self) -> BrowserAppState:
        return self.server.app_state  # type: ignore[attr-defined]

    def _mode(self) -> str:
        return self.server.browser_mode  # type: ignore[attr-defined]

    def _source_payload(self) -> dict:
        return self._state()._source_payload()


__all__ = ["BrowserRequestHandler"]
