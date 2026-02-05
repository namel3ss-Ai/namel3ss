from __future__ import annotations

import json
from types import SimpleNamespace
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from namel3ss.config.loader import load_config
from namel3ss.cli.demo_support import is_demo_project
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.backend.upload_recorder import UploadRecorder, apply_upload_error_payload
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
from namel3ss.ui.actions.dispatch import dispatch_ui_action
from namel3ss.ui.export.contract import build_ui_contract_payload
from namel3ss.ui.external.detect import resolve_external_ui_root
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.version import get_version
from namel3ss.runtime.server.observability_helpers import (
    empty_observability_payload,
    load_observability_builder,
    observability_enabled,
)
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.router.program_state import ProgramState
from namel3ss.runtime.storage.factory import create_store


DEFAULT_SERVICE_PORT = 8787


class ServiceRequestHandler(BaseHTTPRequestHandler):
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
        if path.startswith("/api/"):
            self._handle_api_get(path)
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
                payload = build_error_payload("Invalid JSON body", kind="engine")
                self._respond_json(payload, status=400)
                return
            self._handle_action_post(body)
            return
        if path == "/api/upload":
            response, status = self._handle_upload_post(parsed.query)
            self._respond_json(response, status=status)
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _health_payload(self) -> Dict[str, object]:
        return {
            "ok": True,
            "status": "ready",
            "target": getattr(self.server, "target", "service"),  # type: ignore[attr-defined]
            "process_model": getattr(self.server, "process_model", "service"),  # type: ignore[attr-defined]
            "build_id": getattr(self.server, "build_id", None),  # type: ignore[attr-defined]
            "app_path": getattr(self.server, "app_path", None),  # type: ignore[attr-defined]
            "summary": getattr(self.server, "program_summary", {}),  # type: ignore[attr-defined]
        }

    def _version_payload(self) -> Dict[str, object]:
        return {
            "ok": True,
            "version": get_version(),
            "target": getattr(self.server, "target", "service"),  # type: ignore[attr-defined]
            "build_id": getattr(self.server, "build_id", None),  # type: ignore[attr-defined]
        }

    def _respond_json(self, payload: dict, status: int = 200, *, sort_keys: bool = False) -> None:
        data = json_dumps(payload, sort_keys=sort_keys).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_api_get(self, path: str) -> None:
        normalized = path.rstrip("/") or "/"
        contract_kind = _contract_kind_for_path(normalized)
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
            payload = build_ui_contract_payload(program_ir)
            if kind != "all":
                payload = payload.get(kind, {})
            self._respond_json(payload, status=200, sort_keys=True)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            self._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            self._respond_json(payload, status=500)

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
        try:
            response = dispatch_ui_action(program_ir, action_id=action_id, payload=payload)
            if isinstance(response, dict):
                status = 200 if response.get("ok", True) else 400
                self._respond_json(response, status=status)
            else:  # pragma: no cover - defensive
                payload = build_error_payload("Action response invalid", kind="engine")
                self._respond_json(payload, status=500)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine")
            self._respond_json(payload, status=400)
        except Exception as err:  # pragma: no cover - defensive
            payload = build_error_payload(f"Action failed: {err}", kind="engine")
            self._respond_json(payload, status=500)

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
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive
            payload = build_error_payload(str(err), kind="internal")
            payload = apply_upload_error_payload(payload, recorder)
            return payload, 500

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
            payload = build_error_from_exception(err, kind="engine")
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive
            payload = build_error_payload(str(err), kind="internal")
            return payload, 500

    def _handle_observability(self, kind: str) -> tuple[dict, int]:
        program_ir = self._program()
        if program_ir is None:
            return build_error_payload("Program not loaded", kind="engine"), 500
        if not observability_enabled():
            payload = empty_observability_payload(kind)
            return payload, 200
        builder = load_observability_builder(kind)
        if builder is None:
            payload = empty_observability_payload(kind)
            return payload, 200
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
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        try:
            decoded = raw_body.decode("utf-8") if raw_body else ""
            return json.loads(decoded or "{}")
        except json.JSONDecodeError:
            return None

    def _dispatch_dynamic_route(self) -> bool:
        program = self._ensure_program()
        if program is None:
            return False
        registry = self._route_registry()
        state = self._program_state()
        revision = getattr(state, "revision", None) if state else None
        refresh_routes(program=program, registry=registry, revision=revision, logger=print)
        result = dispatch_route(
            registry=registry,
            method=self.command,
            raw_path=self.path,
            headers=dict(self.headers.items()),
            rfile=self.rfile,
            program=program,
            identity=None,
            auth_context=None,
            store=self._ensure_store(program),
        )
        if result is None:
            return False
        self._respond_json(result.payload, status=result.status, sort_keys=True)
        return True

    def _ensure_program(self):
        state = self._program_state()
        if state is None:
            return getattr(self.server, "program_ir", None)  # type: ignore[attr-defined]
        if state.refresh_if_needed():
            program = state.program
            if program is not None:
                self.server.program_ir = program  # type: ignore[attr-defined]
                self.server.program_summary = _summarize_program(program)  # type: ignore[attr-defined]
        return state.program

    def _route_registry(self) -> RouteRegistry:
        registry = getattr(self.server, "route_registry", None)  # type: ignore[attr-defined]
        if registry is None:
            registry = RouteRegistry()
            self.server.route_registry = registry  # type: ignore[attr-defined]
        return registry

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


class ServiceRunner:
    def __init__(
        self,
        app_path: Path,
        target: str,
        build_id: str | None = None,
        port: int = DEFAULT_SERVICE_PORT,
        *,
        auto_seed: bool = False,
        seed_flow: str = "seed_demo",
    ):
        self.app_path = Path(app_path).resolve()
        self.target = target
        self.build_id = build_id
        self.port = port or DEFAULT_SERVICE_PORT
        self.auto_seed = auto_seed
        self.seed_flow = seed_flow
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.program_summary: Dict[str, object] = {}

    def start(self, *, background: bool = False) -> None:
        program_state = ProgramState(self.app_path)
        program_ir = program_state.program
        if program_ir is None:
            raise Namel3ssError("Program failed to load.")
        self.program_summary = _summarize_program(program_ir)
        if _should_auto_seed(program_ir, self.auto_seed, self.seed_flow):
            _seed_flow(program_ir, self.seed_flow)
        external_ui_root = resolve_external_ui_root(
            getattr(program_ir, "project_root", None),
            getattr(program_ir, "app_path", None),
        )
        server = HTTPServer(("0.0.0.0", self.port), ServiceRequestHandler)
        server.target = self.target  # type: ignore[attr-defined]
        server.build_id = self.build_id  # type: ignore[attr-defined]
        server.app_path = self.app_path.as_posix()  # type: ignore[attr-defined]
        server.process_model = "service"  # type: ignore[attr-defined]
        server.program_summary = self.program_summary  # type: ignore[attr-defined]
        server.program_ir = program_ir  # type: ignore[attr-defined]
        server.program_state = program_state  # type: ignore[attr-defined]
        registry = RouteRegistry()
        refresh_routes(program=program_ir, registry=registry, revision=program_state.revision, logger=print)
        server.route_registry = registry  # type: ignore[attr-defined]
        server.external_ui_root = external_ui_root  # type: ignore[attr-defined]
        server.external_ui_enabled = external_ui_root is not None  # type: ignore[attr-defined]
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


def _summarize_program(program_ir) -> Dict[str, object]:
    return {
        "flows": sorted(flow.name for flow in getattr(program_ir, "flows", [])),
        "pages": sorted(getattr(page, "name", "") for page in getattr(program_ir, "pages", []) if getattr(page, "name", "")),
        "records": sorted(getattr(rec, "name", "") for rec in getattr(program_ir, "records", []) if getattr(rec, "name", "")),
    }


def _contract_kind_for_path(path: str) -> str | None:
    if path in {"/api/ui/contract", "/api/ui/contract.json"}:
        return "all"
    if path in {"/api/ui/contract/ui", "/api/ui/contract/ui.json"}:
        return "ui"
    if path in {"/api/ui/contract/actions", "/api/ui/contract/actions.json"}:
        return "actions"
    if path in {"/api/ui/contract/schema", "/api/ui/contract/schema.json"}:
        return "schema"
    return None


def _should_auto_seed(program_ir, enabled: bool, flow_name: str) -> bool:
    if not enabled or not flow_name:
        return False
    flows = [flow.name for flow in getattr(program_ir, "flows", []) if getattr(flow, "name", None)]
    if flow_name not in flows:
        return False
    project_root = _resolve_project_root(program_ir)
    if not project_root:
        return False
    return is_demo_project(project_root)


def _resolve_project_root(program_ir) -> Path | None:
    root = getattr(program_ir, "project_root", None)
    if isinstance(root, Path):
        return root
    if isinstance(root, str) and root:
        return Path(root)
    app_path = getattr(program_ir, "app_path", None)
    if isinstance(app_path, Path):
        return app_path.parent
    if isinstance(app_path, str) and app_path:
        return Path(app_path).parent
    return None


def _seed_flow(program_ir, flow_name: str) -> None:
    try:
        execute_program_flow(program_ir, flow_name)
    except Exception:
        pass


__all__ = ["DEFAULT_SERVICE_PORT", "ServiceRunner"]
