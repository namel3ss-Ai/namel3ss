from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.demo_support import is_clearorders_demo
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.ui.actions.dispatch import dispatch_ui_action
from namel3ss.ui.export.contract import build_ui_contract_payload
from namel3ss.ui.external.detect import resolve_external_ui_root
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.version import get_version


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
        if self._handle_static(path):
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/action":
            body = self._read_json_body()
            if body is None:
                payload = build_error_payload("Invalid JSON body", kind="engine")
                self._respond_json(payload, status=400)
                return
            self._handle_action_post(body)
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

    def _program(self):
        return getattr(self.server, "program_ir", None)  # type: ignore[attr-defined]


class ServiceRunner:
    def __init__(
        self,
        app_path: Path,
        target: str,
        build_id: str | None = None,
        port: int = DEFAULT_SERVICE_PORT,
        *,
        auto_seed: bool = False,
        seed_flow: str = "seed_orders",
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
        program_ir, _ = load_program(self.app_path.as_posix())
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
    return is_clearorders_demo(project_root)


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
