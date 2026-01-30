from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_recorder import UploadRecorder, apply_upload_error_payload
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.resources import studio_web_root
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.determinism import canonical_json_dumps

from namel3ss.runtime.server.dev.errors import error_from_exception, error_from_message
from namel3ss.runtime.server.dev.state import BrowserAppState


class BrowserRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._handle_api_get(path)
            return
        if self._handle_static(path):
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
            payload, status, headers = self._handle_login_post(body)
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/logout":
            payload, status, headers = self._handle_logout_post()
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/upload":
            response, status = self._handle_upload_post(parsed.query)
            self._respond_json(response, status=status)
            return
        self.send_error(404)

    def _handle_api_get(self, path: str) -> None:
        if path == "/api/session":
            payload, status, headers = self._handle_session_get()
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/ui":
            auth_context = self._auth_context_or_error(kind="manifest")
            if auth_context is None:
                return
            payload = self._state().manifest_payload(identity=auth_context.identity, auth_context=auth_context)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/state":
            auth_context = self._auth_context_or_error(kind="state")
            if auth_context is None:
                return
            payload = self._state().state_payload(identity=auth_context.identity)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/data/status":
            payload = self._data_status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/migrations/status":
            payload = self._migrations_status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/migrations/plan":
            payload = self._migrations_plan_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/uploads":
            response, status = self._handle_upload_list()
            self._respond_json(response, status=status)
            return
        if path == "/api/logs":
            payload = self._observability_payload("logs")
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/traces":
            payload = self._observability_payload("traces")
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/trace":
            payload = self._observability_payload("trace")
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/metrics":
            payload = self._observability_payload("metrics")
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/build":
            payload = self._build_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/deploy":
            payload = self._deploy_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/dev/status":
            payload = self._state().status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/health":
            self._respond_json({"ok": True, "status": "ready", "mode": self._mode()})
            return
        self.send_error(404)

    def _handle_action_post(self, body: dict) -> None:
        if not isinstance(body, dict):
            self._respond_json(build_error_payload("Body must be a JSON object.", kind="engine"), status=400)
            return
        action_id = body.get("id")
        payload = body.get("payload") or {}
        if not isinstance(action_id, str):
            self._respond_json(build_error_payload("Action id is required.", kind="engine"), status=400)
            return
        if not isinstance(payload, dict):
            self._respond_json(build_error_payload("Payload must be an object.", kind="engine"), status=400)
            return
        auth_context = self._auth_context_or_error(kind="engine")
        if auth_context is None:
            return
        response = self._state().run_action(
            action_id,
            payload,
            identity=auth_context.identity,
            auth_context=auth_context,
        )
        status = 200 if response.get("ok", True) else 400
        self._respond_json(response, status=status)

    def _handle_upload_post(self, query: str) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            payload = build_error_payload("Program not loaded.", kind="engine")
            return payload, 500
        upload_name = self.headers.get("X-Upload-Name")
        if not upload_name:
            params = parse_qs(query or "")
            name_values = params.get("name") or []
            upload_name = name_values[0] if name_values else None
        length_header = self.headers.get("Content-Length")
        content_length = None
        if length_header:
            try:
                content_length = int(length_header)
            except ValueError:
                content_length = None
        ctx = SimpleNamespace(
            capabilities=getattr(program, "capabilities", ()),
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        recorder = UploadRecorder()
        try:
            response = handle_upload(
                ctx,
                headers=dict(self.headers.items()),
                rfile=self.rfile,
                content_length=content_length,
                upload_name=upload_name,
                recorder=recorder,
            )
            return response, 200
        except Namel3ssError as err:
            payload = error_from_exception(
                err,
                kind="engine",
                source=self._source_payload(),
                mode=self._mode(),
                debug=self._state().debug,
            )
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard
            payload = error_from_message(
                str(err),
                kind="internal",
                mode=self._mode(),
                debug=self._state().debug,
            )
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 500

    def _handle_upload_list(self) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            payload = build_error_payload("Program not loaded.", kind="engine")
            return payload, 500
        ctx = SimpleNamespace(
            capabilities=getattr(program, "capabilities", ()),
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        try:
            response = handle_upload_list(ctx)
            return response, 200
        except Namel3ssError as err:
            payload = error_from_exception(
                err,
                kind="engine",
                source=self._source_payload(),
                mode=self._mode(),
                debug=self._state().debug,
            )
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard
            payload = error_from_message(
                str(err),
                kind="internal",
                mode=self._mode(),
                debug=self._state().debug,
            )
            return payload, 500

    def _observability_payload(self, kind: str) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine")
        if not _observability_enabled():
            return _empty_observability_payload(kind)
        builder = _load_observability_builder(kind)
        if builder is None:
            return _empty_observability_payload(kind)
        return builder(getattr(program, "project_root", None), getattr(program, "app_path", None))

    def _build_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        return get_build_payload(root, app_path)

    def _deploy_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        return get_deploy_payload(root, app_path, program=program)

    def _data_status_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        try:
            config = load_config(app_path=state.app_path)
            return build_data_status_payload(
                config,
                project_root=state.project_root,
                app_path=state.app_path,
            )
        except Namel3ssError as err:
            return error_from_exception(
                err,
                kind="data",
                source=state._source_payload(),
                mode=self._mode(),
                debug=state.debug,
            )
        except Exception as err:  # pragma: no cover - defensive guard rail
            return error_from_message(
                str(err),
                kind="internal",
                mode=self._mode(),
                debug=state.debug,
            )

    def _migrations_status_payload(self) -> dict:
        return self._migrations_payload(build_migrations_status_payload)

    def _migrations_plan_payload(self) -> dict:
        return self._migrations_payload(build_migrations_plan_payload)

    def _migrations_payload(self, builder) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine")
        try:
            return builder(program, project_root=state.project_root)
        except Namel3ssError as err:
            return error_from_exception(
                err,
                kind="data",
                source=state._source_payload(),
                mode=self._mode(),
                debug=state.debug,
            )
        except Exception as err:  # pragma: no cover - defensive guard rail
            return error_from_message(
                str(err),
                kind="internal",
                mode=self._mode(),
                debug=state.debug,
            )

    def _auth_params(self) -> tuple[object, object | None, object]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        config = load_config(app_path=state.app_path)
        store = state.session.ensure_store(config)
        identity_schema = getattr(program, "identity", None) if program is not None else None
        return config, identity_schema, store

    def _handle_session_get(self) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_session(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _handle_login_post(self, body: dict) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_login(
            dict(self.headers.items()),
            body,
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _handle_logout_post(self) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_logout(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _resolve_auth_context(self) -> object:
        config, identity_schema, store = self._auth_params()
        return resolve_auth_context(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _auth_context_or_error(self, *, kind: str) -> object | None:
        try:
            return self._resolve_auth_context()
        except Namel3ssError as err:
            payload = error_from_exception(
                err,
                kind=kind,
                source=self._state()._source_payload(),
                mode=self._mode(),
                debug=self._state().debug,
            )
            self._respond_json(payload, status=400)
            return None

    def _handle_static(self, path: str) -> bool:
        file_path, content_type = _resolve_runtime_file(path, self._mode())
        if not file_path or not content_type:
            return False
        try:
            content = file_path.read_bytes()
        except OSError:  # pragma: no cover - IO guard
            return False
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def _respond_json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        data = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        if not raw_body:
            return {}
        try:
            decoded = raw_body.decode("utf-8")
            return json.loads(decoded or "{}")
        except Exception:
            return None

    def _state(self) -> BrowserAppState:
        return self.server.app_state  # type: ignore[attr-defined]

    def _mode(self) -> str:
        return self.server.browser_mode  # type: ignore[attr-defined]

    def _source_payload(self) -> dict:
        return self._state()._source_payload()


def _resolve_runtime_file(path: str, mode: str) -> tuple[Path | None, str | None]:
    runtime_root = _runtime_web_root()
    if path in {"/", "/index.html"}:
        filename = "dev.html" if mode == "dev" else "preview.html"
        if mode == "run":
            filename = "preview.html"
        file_path = runtime_root / filename
        if file_path.exists():
            return file_path, "text/html"
    for root in (runtime_root, studio_web_root()):
        file_path, content_type = resolve_external_ui_file(root, path)
        if file_path and content_type:
            return file_path, content_type
    return None, None


def _runtime_web_root() -> Path:
    return Path(__file__).resolve().parents[2] / "web"


def _load_observability_builder(kind: str):
    from namel3ss.runtime import observability_api

    mapping = {
        "logs": observability_api.get_logs_payload,
        "trace": observability_api.get_trace_payload,
        "traces": observability_api.get_traces_payload,
        "metrics": observability_api.get_metrics_payload,
    }
    return mapping.get(kind)


def _observability_enabled() -> bool:
    from namel3ss.observability.enablement import observability_enabled

    return observability_enabled()


def _empty_observability_payload(kind: str) -> dict:
    if kind == "metrics":
        return {"ok": True, "counters": [], "timings": []}
    if kind in {"trace", "traces"}:
        return {"ok": True, "count": 0, "spans": []}
    return {"ok": True, "count": 0, "logs": []}


__all__ = ["BrowserRequestHandler"]
