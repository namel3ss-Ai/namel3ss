from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.docs.spec import build_openapi_spec
from namel3ss.docs.portal_assets import DOCS_HTML
from namel3ss.docs.prompts import collect_prompts
from namel3ss.evals.ai_flow_eval import load_ai_flow_evals
from namel3ss.evals.prompt_eval import load_prompt_evals
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.observability.ai_metrics import apply_thresholds, load_ai_metrics, load_thresholds, summarize_ai_metrics
from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.router.program_state import ProgramState
from namel3ss.studio.session import SessionState


DEFAULT_DOCS_PORT = 7341


class DocsState:
    def __init__(self, app_path: Path) -> None:
        self.program_state = ProgramState(app_path)
        self.registry = RouteRegistry()
        self.session = SessionState()
        self._spec_cache: dict | None = None
        self._spec_revision: str | None = None
        self.error_payload: dict | None = None

    def refresh(self) -> None:
        changed = self.program_state.refresh_if_needed()
        program = self.program_state.program
        if self.program_state.error:
            self.error_payload = build_error_from_exception(self.program_state.error, kind="engine")
            return
        if program is None:
            self.error_payload = build_error_payload("Program not loaded.", kind="engine")
            return
        refresh_routes(program=program, registry=self.registry, revision=self.program_state.revision, logger=None)
        if changed or self._spec_cache is None or self._spec_revision != self.program_state.revision:
            try:
                self._spec_cache = build_openapi_spec(program)
                self._spec_revision = self.program_state.revision
                self.error_payload = None
            except Namel3ssError as err:
                self.error_payload = build_error_from_exception(err, kind="engine")

    @property
    def program(self):
        return self.program_state.program

    @property
    def spec(self) -> dict | None:
        return self._spec_cache


class DocsRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"", "/", "/docs", "/playground"}:
            self._respond_html(DOCS_HTML)
            return
        if path == "/openapi.json":
            payload, status = self._spec_payload()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/metrics":
            payload, status = self._metrics_payload()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/prompts.json":
            payload, status = self._prompts_payload()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path == "/evals.json":
            payload, status = self._evals_payload()
            self._respond_json(payload, status=status, sort_keys=True)
            return
        if path.startswith("/api/"):
            if self._dispatch_dynamic_route():
                return
            self.send_error(404)
            return
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self._dispatch_dynamic_route():
            return
        self.send_error(404)

    def _state(self) -> DocsState:
        return self.server.docs_state  # type: ignore[attr-defined]

    def _ensure_state(self) -> DocsState:
        state = self._state()
        state.refresh()
        return state

    def _spec_payload(self) -> tuple[dict, int]:
        state = self._ensure_state()
        if state.error_payload:
            return state.error_payload, 400
        if state.spec is None:
            return build_error_payload("Spec is unavailable.", kind="engine"), 500
        return state.spec, 200

    def _metrics_payload(self) -> tuple[dict, int]:
        state = self._ensure_state()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        root = getattr(program, "project_root", None)
        app_path = getattr(program, "app_path", None)
        records = load_ai_metrics(root, app_path)
        summary = summarize_ai_metrics(records)
        thresholds = load_thresholds(root, app_path)
        drift = apply_thresholds(summary, thresholds)
        return {"ok": True, "summary": summary, "thresholds": drift}, 200

    def _prompts_payload(self) -> tuple[dict, int]:
        state = self._ensure_state()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        return {"ok": True, "prompts": collect_prompts(program)}, 200

    def _evals_payload(self) -> tuple[dict, int]:
        state = self._ensure_state()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine"), 500
        prompt_entries = load_prompt_evals(getattr(program, "project_root", None), getattr(program, "app_path", None))
        ai_entries = load_ai_flow_evals(getattr(program, "project_root", None), getattr(program, "app_path", None))
        return {"ok": True, "evals": prompt_entries, "ai_evals": ai_entries}, 200

    def _dispatch_dynamic_route(self) -> bool:
        state = self._ensure_state()
        if state.error_payload:
            self._respond_json(state.error_payload, status=400)
            return True
        program = state.program
        if program is None:
            self._respond_json(build_error_payload("Program not loaded.", kind="engine"), status=500)
            return True
        config = load_config(app_path=getattr(program, "app_path", None), root=getattr(program, "project_root", None))
        store = state.session.ensure_store(config)
        result = dispatch_route(
            registry=state.registry,
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
        self._respond_json(result.payload, status=result.status)
        return True

    def _respond_json(self, payload: dict, status: int = 200, *, sort_keys: bool = False) -> None:
        data = canonical_json_dumps(payload, pretty=True, drop_run_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond_html(self, payload: str) -> None:
        data = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class DocsRunner:
    def __init__(self, app_path: Path, *, port: int = DEFAULT_DOCS_PORT) -> None:
        self.app_path = Path(app_path).resolve()
        self.port = port or DEFAULT_DOCS_PORT
        self.server: HTTPServer | None = None

    def bind(self) -> None:
        if self.server:
            return
        server = _bind_http_server(self.port, DocsRequestHandler)
        server.docs_state = DocsState(self.app_path)  # type: ignore[attr-defined]
        self.port = int(server.server_address[1])
        self.server = server

    def start(self, *, background: bool = False) -> None:
        self.bind()
        assert self.server is not None
        if background:
            import threading

            thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            thread.start()
        else:
            self.server.serve_forever()

    def shutdown(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass


def _bind_http_server(port: int, handler) -> HTTPServer:
    base = port or DEFAULT_DOCS_PORT
    last_error: Exception | None = None
    for offset in range(0, 20):
        candidate = base + offset
        try:
            return HTTPServer(("127.0.0.1", candidate), handler)
        except OSError as err:  # pragma: no cover - bind guard
            last_error = err
            continue
    raise last_error or OSError("Unable to bind HTTP server")


__all__ = ["DocsRunner", "DEFAULT_DOCS_PORT"]
