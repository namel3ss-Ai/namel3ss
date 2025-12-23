from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from namel3ss.cli.app_loader import load_program
from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.version import get_version


DEFAULT_SERVICE_PORT = 8787


class ServiceRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/health"):
            self._respond_json(self._health_payload())
            return
        if self.path.startswith("/version"):
            self._respond_json(self._version_payload())
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

    def _respond_json(self, payload: dict, status: int = 200) -> None:
        data = json_dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ServiceRunner:
    def __init__(self, app_path: Path, target: str, build_id: str | None = None, port: int = DEFAULT_SERVICE_PORT):
        self.app_path = Path(app_path).resolve()
        self.target = target
        self.build_id = build_id
        self.port = port or DEFAULT_SERVICE_PORT
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.program_summary: Dict[str, object] = {}

    def start(self, *, background: bool = False) -> None:
        program_ir, _ = load_program(self.app_path.as_posix())
        self.program_summary = _summarize_program(program_ir)
        server = HTTPServer(("0.0.0.0", self.port), ServiceRequestHandler)
        server.target = self.target  # type: ignore[attr-defined]
        server.build_id = self.build_id  # type: ignore[attr-defined]
        server.app_path = self.app_path.as_posix()  # type: ignore[attr-defined]
        server.process_model = "service"  # type: ignore[attr-defined]
        server.program_summary = self.program_summary  # type: ignore[attr-defined]
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


__all__ = ["DEFAULT_SERVICE_PORT", "ServiceRunner"]
