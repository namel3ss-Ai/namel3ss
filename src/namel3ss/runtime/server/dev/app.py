from __future__ import annotations

import threading
from http.server import HTTPServer
from pathlib import Path

from namel3ss.runtime.server.dev.routes import BrowserRequestHandler
from namel3ss.runtime.server.dev.state import BrowserAppState


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
        self.app_state = BrowserAppState(
            self.app_path,
            mode=mode,
            debug=debug,
            watch_sources=watch_sources,
            engine_target=engine_target,
        )

    def bind(self) -> None:
        if self.server:
            return
        server = _bind_http_server(self.port, BrowserRequestHandler)
        self.port = int(server.server_address[1])
        server.browser_mode = self.mode  # type: ignore[attr-defined]
        server.app_state = self.app_state  # type: ignore[attr-defined]
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


def _bind_http_server(port: int, handler) -> HTTPServer:
    base = port or DEFAULT_BROWSER_PORT
    last_error: Exception | None = None
    for offset in range(0, 20):
        candidate = base + offset
        try:
            return HTTPServer(("127.0.0.1", candidate), handler)
        except OSError as err:  # pragma: no cover - bind guard
            last_error = err
            continue
    raise last_error or OSError("Unable to bind HTTP server")


__all__ = ["BrowserRunner", "DEFAULT_BROWSER_PORT"]
