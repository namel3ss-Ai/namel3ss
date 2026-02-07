from __future__ import annotations

from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_recorder import UploadRecorder, apply_upload_error_payload
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.server.observability_helpers import (
    empty_observability_payload,
    load_observability_builder,
    observability_enabled,
)
from namel3ss.runtime.server.service_sessions_api import (
    cleanup_session_manager,
    handle_remote_studio_get,
    handle_session_action_post,
    handle_session_create_post,
    handle_session_kill_delete,
    handle_session_list_get,
    handle_session_manifest_get,
    handle_session_state_get,
    resolve_dynamic_route_context,
    session_manager,
)
from namel3ss.runtime.server.utils import dispatch_dynamic_route, get_or_create_route_registry, read_json_body
from namel3ss.runtime.server.webhook_triggers import handle_webhook_trigger_post
from namel3ss.runtime.service_helpers import contract_kind_for_path, summarize_program
from namel3ss.runtime.storage.factory import create_store
from namel3ss.ui.actions.dispatch import dispatch_ui_action
from namel3ss.ui.export.contract import build_ui_contract_payload
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.utils.json_tools import dumps as json_dumps


class ServiceRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        cleanup_session_manager(self)
        if path.startswith("/health"):
            from namel3ss.runtime.server.metadata_payloads import build_health_payload

            self._respond_json(build_health_payload(self.server))
            return
        if path.startswith("/version"):
            from namel3ss.runtime.server.metadata_payloads import build_version_payload

            self._respond_json(build_version_payload(self.server))
            return
        if path.startswith("/api/"):
            self._handle_api_get(parsed)
            return
        if self._dispatch_dynamic_route():
            return
        if self._handle_static(path):
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        cleanup_session_manager(self)
        if path == "/api/ui/action":
            path = "/api/action"
        if path == "/api/action":
            body = self._read_json_body()
            if body is None:
                self._respond_json(build_error_payload("Invalid JSON body", kind="engine"), status=400)
                return
            self._handle_action_post(body)
            return
        if path == "/api/service/sessions":
            body = self._read_json_body()
            if body is None:
                self._respond_json(build_error_payload("Invalid JSON body", kind="engine"), status=400)
                return
            handle_session_create_post(self, body)
            return
        if path == "/api/upload":
            response, status = self._handle_upload_post(parsed.query)
            self._respond_json(response, status=status)
            return
        if handle_webhook_trigger_post(
            path=path,
            program=self._program(),
            read_json_body=self._read_json_body,
            respond_json=self._respond_json,
        ):
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        cleanup_session_manager(self)
        if path.startswith("/api/service/sessions/"):
            session_id = path.rsplit("/", 1)[-1]
            handle_session_kill_delete(self, session_id)
            return
        self.send_error(404)

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

    def _respond_body(
        self,
        body: bytes,
        *,
        content_type: str,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _handle_api_get(self, parsed) -> None:
        normalized = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query or "")
        if normalized == "/api/service/sessions":
            handle_session_list_get(self)
            return
        if normalized.startswith("/api/service/studio/"):
            handle_remote_studio_get(self, normalized)
            return
        if normalized == "/api/ui/manifest":
            if session_manager(self) is not None:
                handle_session_manifest_get(self, query)
                return
            self._respond_contract("ui")
            return
        if normalized == "/api/ui/actions":
            self._respond_contract("actions")
            return
        if normalized == "/api/ui/state":
            if session_manager(self) is not None:
                handle_session_state_get(self, query)
                return
            state = self._program_state()
            revision = getattr(state, "revision", "") if state is not None else ""
            payload = {
                "ok": True,
                "api_version": "1",
                "state": {"current_page": None, "values": {}, "errors": []},
                "revision": revision,
            }
            self._respond_json(payload, status=200, sort_keys=True)
            return
        contract_kind = contract_kind_for_path(normalized)
        if contract_kind is not None:
            self._respond_contract(contract_kind)
            return
        if normalized == "/api/uploads":
            response, status = self._handle_upload_list()
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/logs":
            response, status = self._handle_observability("logs")
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/traces":
            response, status = self._handle_observability("traces")
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/trace":
            response, status = self._handle_observability("trace")
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/metrics":
            response, status = self._handle_observability("metrics")
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/build":
            response, status = self._handle_build()
            self._respond_json(response, status=status, sort_keys=True)
            return
        if normalized == "/api/deploy":
            response, status = self._handle_deploy()
            self._respond_json(response, status=status, sort_keys=True)
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _respond_contract(self, kind: str) -> None:
        program_ir = self._program()
        if program_ir is None:
            self._respond_json(build_error_payload("Program not loaded", kind="engine"), status=500)
            return
        try:
            ui_mode = getattr(self.server, "ui_mode", "production")  # type: ignore[attr-defined]
            payload = build_ui_contract_payload(program_ir, ui_mode=ui_mode)
            if kind != "all":
                payload = payload.get(kind, {})
            self._respond_json(payload, status=200, sort_keys=True)
        except Namel3ssError as err:
            self._respond_json(build_error_from_exception(err, kind="engine"), status=400)
        except Exception as err:  # pragma: no cover - defensive guard rail
            self._respond_json(build_error_payload(str(err), kind="internal"), status=500)

    def _handle_action_post(self, body: dict) -> None:
        if not isinstance(body, dict):
            self._respond_json(build_error_payload("Body must be a JSON object", kind="engine"), status=400)
            return
        action_id = body.get("id")
        payload = body.get("payload") or {}
        if not isinstance(action_id, str):
            self._respond_json(build_error_payload("Action id is required", kind="engine"), status=400)
            return
        if not isinstance(payload, dict):
            self._respond_json(build_error_payload("Payload must be an object", kind="engine"), status=400)
            return
        program_ir = self._program()
        if program_ir is None:
            self._respond_json(build_error_payload("Program not loaded", kind="engine"), status=500)
            return
        if session_manager(self) is not None:
            handle_session_action_post(self, body, action_id=action_id, payload=payload, program_ir=program_ir)
            return
        try:
            worker_pool = getattr(self.server, "worker_pool", None)  # type: ignore[attr-defined]
            if worker_pool is not None:
                response = worker_pool.run_action(action_id, payload)
            else:
                ui_mode = getattr(self.server, "ui_mode", "production")  # type: ignore[attr-defined]
                response = dispatch_ui_action(program_ir, action_id=action_id, payload=payload, ui_mode=ui_mode)
            if isinstance(response, dict):
                if worker_pool is not None:
                    response.setdefault("process_model", "worker_pool")
                status = 200 if response.get("ok", True) else 400
                self._respond_json(response, status=status)
                return
            self._respond_json(build_error_payload("Action response invalid", kind="engine"), status=500)
        except Namel3ssError as err:
            self._respond_json(build_error_from_exception(err, kind="engine"), status=400)
        except Exception as err:  # pragma: no cover - defensive
            self._respond_json(build_error_payload(f"Action failed: {err}", kind="engine"), status=500)

    def _handle_upload_post(self, query: str) -> tuple[dict, int]:
        program_ir = self._program()
        if program_ir is None:
            return build_error_payload("Program not loaded", kind="engine"), 500
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
            capabilities=getattr(program_ir, "capabilities", ()),
            project_root=getattr(program_ir, "project_root", None),
            app_path=getattr(program_ir, "app_path", None),
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
            return apply_upload_error_payload(payload, recorder), 400
        except Exception as err:  # pragma: no cover - defensive
            payload = build_error_payload(str(err), kind="internal")
            return apply_upload_error_payload(payload, recorder), 500

    def _handle_upload_list(self) -> tuple[dict, int]:
        program_ir = self._program()
        if program_ir is None:
            return build_error_payload("Program not loaded", kind="engine"), 500
        ctx = SimpleNamespace(
            capabilities=getattr(program_ir, "capabilities", ()),
            project_root=getattr(program_ir, "project_root", None),
            app_path=getattr(program_ir, "app_path", None),
        )
        try:
            response = handle_upload_list(ctx)
            return response, 200
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="engine"), 400
        except Exception as err:  # pragma: no cover - defensive
            return build_error_payload(str(err), kind="internal"), 500

    def _handle_observability(self, kind: str) -> tuple[dict, int]:
        program_ir = self._program()
        if program_ir is None:
            return build_error_payload("Program not loaded", kind="engine"), 500
        if not observability_enabled():
            return empty_observability_payload(kind), 200
        builder = load_observability_builder(kind)
        if builder is None:
            return empty_observability_payload(kind), 200
        payload = builder(getattr(program_ir, "project_root", None), getattr(program_ir, "app_path", None))
        status = 200 if payload.get("ok", True) else 400
        return payload, status

    def _handle_build(self) -> tuple[dict, int]:
        program_ir = self._program()
        root = getattr(program_ir, "project_root", None) if program_ir is not None else None
        app_path = getattr(program_ir, "app_path", None) if program_ir is not None else None
        payload = get_build_payload(root, app_path)
        status = 200 if payload.get("ok", True) else 400
        return payload, status

    def _handle_deploy(self) -> tuple[dict, int]:
        program_ir = self._program()
        root = getattr(program_ir, "project_root", None) if program_ir is not None else None
        app_path = getattr(program_ir, "app_path", None) if program_ir is not None else None
        payload = get_deploy_payload(root, app_path, program=program_ir, target=getattr(self.server, "target", None))
        status = 200 if payload.get("ok", True) else 400
        return payload, status

    def _handle_static(self, path: str) -> bool:
        if bool(getattr(self.server, "headless", False)):  # type: ignore[attr-defined]
            return False
        ui_root = getattr(self.server, "external_ui_root", None)  # type: ignore[attr-defined]
        if ui_root is None:
            return False
        file_path, content_type = resolve_external_ui_file(ui_root, path)
        if not file_path or not content_type:
            return False
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def _read_json_body(self) -> dict | None:
        return read_json_body(dict(self.headers.items()), self.rfile)

    def _dispatch_dynamic_route(self) -> bool:
        program = self._ensure_program()
        if program is None:
            return False
        worker_pool = getattr(self.server, "worker_pool", None)  # type: ignore[attr-defined]
        try:
            flow_executor, store, identity, extra_headers = resolve_dynamic_route_context(self, program, worker_pool)
        except Namel3ssError as err:
            self._respond_json(build_error_from_exception(err, kind="engine"), status=400)
            return True
        result = dispatch_dynamic_route(
            registry=self._route_registry(),
            method=self.command,
            raw_path=self.path,
            headers=dict(self.headers.items()),
            rfile=self.rfile,
            program=program,
            state=self._program_state(),
            store=store,
            flow_executor=flow_executor,
            identity=identity,
            auth_context=None,
        )
        if result is None:
            return False
        headers = dict(result.headers or {})
        headers.update(extra_headers)
        if result.body is not None and result.content_type:
            self._respond_body(
                result.body,
                content_type=result.content_type,
                status=result.status,
                headers=headers,
            )
            return True
        self._respond_json(result.payload or {}, status=result.status, sort_keys=True, headers=headers)
        return True

    def _ensure_program(self):
        state = self._program_state()
        if state is None:
            return getattr(self.server, "program_ir", None)  # type: ignore[attr-defined]
        if state.refresh_if_needed():
            program = state.program
            if program is not None:
                self.server.program_ir = program  # type: ignore[attr-defined]
                self.server.program_summary = summarize_program(program)  # type: ignore[attr-defined]
        return state.program

    def _route_registry(self) -> RouteRegistry:
        return get_or_create_route_registry(self.server)

    def _ensure_store(self, program):
        store = getattr(self.server, "flow_store", None)  # type: ignore[attr-defined]
        if store is not None:
            return store
        config = load_config(
            app_path=getattr(program, "app_path", None),
            root=getattr(program, "project_root", None),
        )
        store = create_store(config=config)
        self.server.flow_store = store  # type: ignore[attr-defined]
        return store

    def _program_state(self):
        return getattr(self.server, "program_state", None)  # type: ignore[attr-defined]

    def _program(self):
        return self._ensure_program()


__all__ = ["ServiceRequestHandler"]
