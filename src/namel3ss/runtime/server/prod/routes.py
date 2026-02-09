from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.errors.normalize import attach_runtime_error_payload
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_recorder import UploadRecorder, apply_upload_error_payload
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.runtime.dev_server import BrowserAppState
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.server.prod import answer_explain, documents
from namel3ss.runtime.server.observability_helpers import (
    empty_observability_payload,
    load_observability_builder,
    observability_enabled,
)
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.version import get_version
class ProductionRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass
    def do_GET(self) -> None:  # noqa: N802
        raw_path = self.path
        path = urlparse(raw_path).path
        if path.startswith("/health"):
            self._respond_json(self._health_payload())
            return
        if path.startswith("/version"):
            self._respond_json(self._version_payload())
            return
        if path == "/api/session":
            payload, status, headers = self._handle_session_get()
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/ui":
            auth_context = self._auth_context_or_error(kind="manifest")
            if auth_context is None:
                return
            payload = self._state().manifest_payload(
                identity=getattr(auth_context, "identity", None),
                auth_context=auth_context,
            )
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/data/status":
            payload, status = self._handle_data_status()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/migrations/status":
            payload, status = self._handle_migrations(build_migrations_status_payload)
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/migrations/plan":
            payload, status = self._handle_migrations(build_migrations_plan_payload)
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/uploads":
            response, status = self._handle_upload_list()
            self._respond_json(response, status=status)
            return
        if answer_explain.handle_answer_explain_get(self, path):
            return
        if documents.handle_documents_get(self, raw_path):
            return
        if path == "/api/logs":
            payload, status = self._handle_observability("logs")
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/traces":
            payload, status = self._handle_observability("traces")
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/trace":
            payload, status = self._handle_observability("trace")
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/metrics":
            payload, status = self._handle_observability("metrics")
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/build":
            payload, status = self._handle_build()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/deploy":
            payload, status = self._handle_deploy()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path.startswith("/api/"):
            if self._dispatch_dynamic_route():
                return
            self.send_error(404)
            return
        if self._dispatch_dynamic_route():
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
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _health_payload(self) -> dict:
        return {
            "ok": True,
            "status": "ready",
            "target": getattr(self.server, "target", "service"),  # type: ignore[attr-defined]
            "build_id": getattr(self.server, "build_id", None),  # type: ignore[attr-defined]
        }

    def _version_payload(self) -> dict:
        return {
            "ok": True,
            "version": get_version(),
            "target": getattr(self.server, "target", "service"),  # type: ignore[attr-defined]
            "build_id": getattr(self.server, "build_id", None),  # type: ignore[attr-defined]
        }
    def _respond_json(
        self,
        payload: dict,
        status: int = 200,
        *,
        sort_keys: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        data = json_dumps(payload, sort_keys=sort_keys).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)
    def _respond_bytes(
        self,
        payload: bytes,
        *,
        status: int = 200,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)
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
        auth_context = self._auth_context_or_error(kind="engine")
        if auth_context is None:
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
            identity=getattr(auth_context, "identity", None),
            auth_context=auth_context,
            store=store,
        )
        if result is None:
            return False
        if result.body is not None:
            self._respond_bytes(
                result.body,
                status=result.status,
                content_type=result.content_type or "application/octet-stream",
                headers=result.headers,
            )
            return True
        self._respond_json(result.payload or {}, status=result.status, headers=result.headers)
        return True
    def _handle_action_post(self, body: dict) -> None:
        if not isinstance(body, dict):
            payload = build_error_payload("Body must be a JSON object.", kind="engine")
            payload = attach_runtime_error_payload(payload, status_code=400, endpoint="/api/action")
            self._respond_json(payload, status=400)
            return
        action_id = body.get("id")
        payload = body.get("payload") or {}
        if not isinstance(action_id, str):
            response = build_error_payload("Action id is required.", kind="engine")
            response = attach_runtime_error_payload(response, status_code=400, endpoint="/api/action")
            self._respond_json(response, status=400)
            return
        if not isinstance(payload, dict):
            response = build_error_payload("Payload must be an object.", kind="engine")
            response = attach_runtime_error_payload(response, status_code=400, endpoint="/api/action")
            self._respond_json(response, status=400)
            return
        auth_context = self._auth_context_or_error(kind="engine")
        if auth_context is None:
            return
        try:
            response = self._state().run_action(
                action_id,
                payload,
                identity=getattr(auth_context, "identity", None),
                auth_context=auth_context,
            )
            response = attach_runtime_error_payload(response, endpoint="/api/action")
            status = 200 if response.get("ok", True) else 400
            self._respond_json(response, status=status)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            payload = attach_runtime_error_payload(payload, status_code=400, endpoint="/api/action")
            self._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            payload = attach_runtime_error_payload(payload, status_code=500, endpoint="/api/action")
            self._respond_json(payload, status=500)
    def _handle_upload_post(self, query: str) -> tuple[dict, int]:
        program = getattr(self._state(), "program", None)
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
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
            payload = build_error_from_exception(err, kind="engine")
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 500
    def _handle_upload_list(self) -> tuple[dict, int]:
        program = getattr(self._state(), "program", None)
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        ctx = SimpleNamespace(
            capabilities=getattr(program, "capabilities", ()),
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        try:
            response = handle_upload_list(ctx)
            return response, 200
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            return payload, 500
    def _handle_observability(self, kind: str) -> tuple[dict, int]:
        program = getattr(self._state(), "program", None)
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        if not observability_enabled():
            payload = empty_observability_payload(kind)
            return payload, 200
        builder = load_observability_builder(kind)
        if builder is None:
            payload = empty_observability_payload(kind)
            return payload, 200
        payload = builder(getattr(program, "project_root", None), getattr(program, "app_path", None))
        status = 200 if payload.get("ok", True) else 400
        return payload, status
    def _handle_build(self) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = getattr(state, "program", None)
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        payload = get_build_payload(root, app_path)
        status = 200 if payload.get("ok", True) else 400
        return payload, status
    def _handle_deploy(self) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = getattr(state, "program", None)
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        payload = get_deploy_payload(root, app_path, program=program, target=getattr(self.server, "target", None))
        status = 200 if payload.get("ok", True) else 400
        return payload, status
    def _handle_data_status(self) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        try:
            config = load_config(app_path=state.app_path)
            payload = build_data_status_payload(
                config,
                project_root=state.project_root,
                app_path=state.app_path,
            )
            status = 200 if payload.get("ok", True) else 400
            return payload, status
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="data"), 400
        except Exception as err:  # pragma: no cover - defensive guard rail
            return build_error_payload(str(err), kind="internal"), 500
    def _handle_migrations(self, builder) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        try:
            payload = builder(program, project_root=state.project_root)
            status = 200 if payload.get("ok", True) else 400
            return payload, status
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="data"), 400
        except Exception as err:  # pragma: no cover - defensive guard rail
            return build_error_payload(str(err), kind="internal"), 500
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
            project_root=str(getattr(self._state(), "project_root", "") or "") or None,
            app_path=str(getattr(self._state(), "app_path", "") or "") or None,
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
            project_root=str(getattr(self._state(), "project_root", "") or "") or None,
            app_path=str(getattr(self._state(), "app_path", "") or "") or None,
        )

    def _resolve_auth_context(self) -> object:
        config, identity_schema, store = self._auth_params()
        return resolve_auth_context(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
            project_root=str(getattr(self._state(), "project_root", "") or "") or None,
            app_path=str(getattr(self._state(), "app_path", "") or "") or None,
        )

    def _auth_context_or_error(self, *, kind: str) -> object | None:
        try:
            return self._resolve_auth_context()
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind=kind)
            self._respond_json(payload, status=400)
            return None

    def _handle_static(self, path: str) -> bool:
        web_root = getattr(self.server, "web_root", None)  # type: ignore[attr-defined]
        if web_root is None:
            return False
        file_path, content_type = resolve_external_ui_file(web_root, path)
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
__all__ = ["ProductionRequestHandler"]
