from __future__ import annotations

import json
from types import SimpleNamespace
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.dev_server import BrowserAppState
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.observability_api import (
    get_logs_payload,
    get_metrics_payload,
    get_trace_payload,
    get_traces_payload,
)
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.version import get_version


DEFAULT_START_PORT = 8787


class ProductionRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
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
        if path == "/api/logs":
            payload, status = self._handle_observability(get_logs_payload)
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/traces":
            payload, status = self._handle_observability(get_traces_payload)
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/trace":
            payload, status = self._handle_observability(get_trace_payload)
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/api/metrics":
            payload, status = self._handle_observability(get_metrics_payload)
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
            self.send_error(404)
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
        try:
            response = self._state().run_action(
                action_id,
                payload,
                identity=getattr(auth_context, "identity", None),
                auth_context=auth_context,
            )
            status = 200 if response.get("ok", True) else 400
            self._respond_json(response, status=status)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            self._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
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
        try:
            response = handle_upload(
                ctx,
                headers=dict(self.headers.items()),
                rfile=self.rfile,
                content_length=content_length,
                upload_name=upload_name,
            )
            return response, 200
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
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

    def _handle_observability(self, builder) -> tuple[dict, int]:
        program = getattr(self._state(), "program", None)
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
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


class ProductionRunner:
    def __init__(
        self,
        build_path: Path,
        app_path: Path,
        *,
        build_id: str | None,
        target: str = "service",
        port: int = DEFAULT_START_PORT,
        artifacts: dict | None = None,
    ) -> None:
        self.build_path = Path(build_path).resolve()
        self.app_path = Path(app_path).resolve()
        self.build_id = build_id
        self.target = target
        self.port = port or DEFAULT_START_PORT
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.artifacts = artifacts or {}
        self.web_root = self._resolve_web_root(self.artifacts)
        self.app_state = BrowserAppState(
            self.app_path,
            mode="preview",
            debug=False,
            source_overrides=_build_source_overrides(self.build_path, self.app_path.parent, self.artifacts),
            watch_sources=False,
            engine_target=self.target,
        )

    def start(self, *, background: bool = False) -> None:
        server = HTTPServer(("0.0.0.0", self.port), ProductionRequestHandler)
        server.target = self.target  # type: ignore[attr-defined]
        server.build_id = self.build_id  # type: ignore[attr-defined]
        server.web_root = self.web_root  # type: ignore[attr-defined]
        server.app_state = self.app_state  # type: ignore[attr-defined]
        self.server = server
        if background:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._thread = thread
        else:
            server.serve_forever()

    def shutdown(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    @property
    def bound_port(self) -> int:
        if self.server:
            return int(self.server.server_address[1])
        return self.port

    def _resolve_web_root(self, artifacts: dict) -> Path:
        web_dir = artifacts.get("web") if isinstance(artifacts, dict) else None
        web_root = self.build_path / (web_dir or "web")
        if not web_root.exists():
            raise Namel3ssError(
                build_guidance_message(
                    what="Build web assets are missing.",
                    why="The build output does not include the runtime web bundle.",
                    fix="Re-run `n3 build` for this target.",
                    example="n3 build --target service",
                )
            )
        return web_root


def _build_source_overrides(build_path: Path, project_root: Path, artifacts: dict) -> dict[Path, str]:
    program_dir = artifacts.get("program") if isinstance(artifacts, dict) else None
    program_root = build_path / (program_dir or "program")
    if not program_root.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Build program snapshot is missing.",
                why="The build output does not include program sources.",
                fix="Re-run `n3 build` for this target.",
                example="n3 build --target service",
            )
        )
    overrides: dict[Path, str] = {}
    for src_path in sorted(program_root.rglob("*.ai"), key=lambda path: path.as_posix()):
        rel = src_path.relative_to(program_root)
        target_path = project_root / rel
        overrides[target_path] = src_path.read_text(encoding="utf-8")
    if not overrides:
        raise Namel3ssError(
            build_guidance_message(
                what="Build program snapshot is empty.",
                why="No .ai sources were found in the build output.",
                fix="Re-run `n3 build` for this target.",
                example="n3 build --target service",
            )
        )
    return overrides


__all__ = ["DEFAULT_START_PORT", "ProductionRunner"]
