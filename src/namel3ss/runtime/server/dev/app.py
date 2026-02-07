from __future__ import annotations

import os
import threading
from http.server import HTTPServer
from pathlib import Path

from namel3ss.runtime.server.concurrency import create_runtime_http_server, load_concurrency_config
from namel3ss.runtime.server.dev.routes import BrowserRequestHandler
from namel3ss.runtime.server.dev.state import BrowserAppState
from namel3ss.ui.manifest.display_mode import (
    DISPLAY_MODE_PRODUCTION,
    DISPLAY_MODE_STUDIO,
    normalize_display_mode,
)
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry


DEFAULT_BROWSER_PORT = 7340


class BrowserRunner:
    def __init__(
        self,
        app_path: Path,
        *,
        mode: str = "dev",
        port: int = DEFAULT_BROWSER_PORT,
        debug: bool = False,
        watch_sources: bool = True,
        engine_target: str = "local",
        headless: bool = False,
        ui_mode: str | None = None,
    ) -> None:
        if mode not in {"dev", "preview", "run"}:
            raise ValueError(f"Unknown browser mode: {mode}")
        self.app_path = Path(app_path).resolve()
        self.mode = mode
        self.port = port or DEFAULT_BROWSER_PORT
        self.debug = debug
        self._thread: threading.Thread | None = None
        self.server: HTTPServer | None = None
        self.watch_sources = watch_sources
        self.headless = headless
        default_ui_mode = DISPLAY_MODE_PRODUCTION if mode in {"run", "preview"} else DISPLAY_MODE_STUDIO
        env_mode = os.getenv("N3_UI_MODE")
        chosen_ui_mode = ui_mode if ui_mode is not None else env_mode
        self.ui_mode = normalize_display_mode(chosen_ui_mode, default=default_ui_mode)
        self.concurrency = load_concurrency_config(app_path=self.app_path)
        self.app_state = BrowserAppState(
            self.app_path,
            mode=mode,
            debug=debug,
            watch_sources=watch_sources,
            engine_target=engine_target,
            ui_mode=self.ui_mode,
        )

    def bind(self) -> None:
        if self.server:
            return
        server = _bind_http_server(self.port, BrowserRequestHandler, config=self.concurrency)
        self.port = int(server.server_address[1])
        server.browser_mode = self.mode  # type: ignore[attr-defined]
        server.app_state = self.app_state  # type: ignore[attr-defined]
        server.concurrency = self.concurrency.to_dict()  # type: ignore[attr-defined]
        server.headless = self.headless  # type: ignore[attr-defined]
        self.app_state._refresh_if_needed()
        registry = RouteRegistry()
        if self.app_state.program is not None:
            refresh_routes(program=self.app_state.program, registry=registry, revision=self.app_state.revision, logger=print)
        server.route_registry = registry  # type: ignore[attr-defined]
        self.server = server

    def start(self, *, background: bool = False) -> None:
        self.bind()
        assert self.server is not None
        if background:
            thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            thread.start()
            self._thread = thread
        else:
            self.server.serve_forever()

    def shutdown(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    @property
    def bound_port(self) -> int:
        if self.server:
            return int(self.server.server_address[1])
        return self.port


def _bind_http_server(port: int, handler, *, config) -> HTTPServer:
    base = port or DEFAULT_BROWSER_PORT
    last_error: Exception | None = None
    for offset in range(0, 20):
        candidate = base + offset
        try:
            return create_runtime_http_server("127.0.0.1", candidate, handler, config=config)
        except OSError as err:  # pragma: no cover - bind guard
            last_error = err
            continue
    raise last_error or OSError("Unable to bind HTTP server")


__all__ = ["BrowserRunner", "DEFAULT_BROWSER_PORT"]
