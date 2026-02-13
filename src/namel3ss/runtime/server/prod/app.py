from __future__ import annotations

import os
import threading
from http.server import HTTPServer
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.dev_server import BrowserAppState
from namel3ss.runtime.server.concurrency import create_runtime_http_server, load_concurrency_config
from namel3ss.runtime.server.headless_api import normalize_api_token, normalize_cors_origins
from namel3ss.runtime.server.lock import (
    RuntimePortLease,
    acquire_runtime_port_lock,
    release_runtime_port_lock,
)
from namel3ss.runtime.server.prod.headless_routes import HeadlessProductionRequestHandler
from namel3ss.runtime.server.prod.security_requirements import build_tls_context_if_required
from namel3ss.runtime.server.prod.routes import ProductionRequestHandler
from namel3ss.runtime.server.startup import (
    build_runtime_startup_context,
    print_startup_banner,
)
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.studio.startup import validate_renderer_registry_startup
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_PRODUCTION


DEFAULT_START_PORT = 8787


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
        headless: bool = False,
        headless_api_token: str | None = None,
        headless_cors_origins: tuple[str, ...] | None = None,
    ) -> None:
        self.build_path = Path(build_path).resolve()
        self.app_path = Path(app_path).resolve()
        self.build_id = build_id
        self.target = target
        self.port = port or DEFAULT_START_PORT
        self.headless = headless
        self.headless_api_token = normalize_api_token(headless_api_token or os.getenv("N3_HEADLESS_API_TOKEN"))
        if headless_cors_origins:
            self.headless_cors_origins = normalize_cors_origins(headless_cors_origins)
        else:
            self.headless_cors_origins = normalize_cors_origins(os.getenv("N3_HEADLESS_CORS_ORIGINS"))
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port_lease: RuntimePortLease | None = None
        self._serve_started = False
        self.artifacts = artifacts or {}
        self.concurrency = load_concurrency_config(app_path=self.app_path)
        if not self.headless:
            validate_renderer_registry_startup()
        self.web_root = None if self.headless else self._resolve_web_root(self.artifacts)
        self.app_state = BrowserAppState(
            self.app_path,
            mode="preview",
            debug=False,
            source_overrides=_build_source_overrides(self.build_path, self.app_path.parent, self.artifacts),
            watch_sources=False,
            engine_target=self.target,
            ui_mode=DISPLAY_MODE_PRODUCTION,
        )

    def start(self, *, background: bool = False) -> None:
        handler = HeadlessProductionRequestHandler if self.headless else ProductionRequestHandler
        self._port_lease = acquire_runtime_port_lock(
            host="0.0.0.0",
            port=self.port,
            app_path=self.app_path,
            mode=self.target or "service",
            allow_reentrant=False,
        )
        try:
            server = create_runtime_http_server("0.0.0.0", self.port, handler, config=self.concurrency)
        except Exception:
            release_runtime_port_lock(self._port_lease)
            self._port_lease = None
            raise
        try:
            self.port = int(server.server_address[1])
            tls_context = build_tls_context_if_required(project_root=self.app_path.parent, app_path=self.app_path)
            if tls_context is not None:
                server.socket = tls_context.wrap_socket(server.socket, server_side=True)
                server.is_tls = True  # type: ignore[attr-defined]
            else:
                server.is_tls = False  # type: ignore[attr-defined]
            server.target = self.target  # type: ignore[attr-defined]
            server.build_id = self.build_id  # type: ignore[attr-defined]
            server.web_root = self.web_root  # type: ignore[attr-defined]
            server.headless = self.headless  # type: ignore[attr-defined]
            server.headless_api_token = self.headless_api_token  # type: ignore[attr-defined]
            server.headless_cors_origins = self.headless_cors_origins  # type: ignore[attr-defined]
            server.app_state = self.app_state  # type: ignore[attr-defined]
            server.concurrency = self.concurrency.to_dict()  # type: ignore[attr-defined]
            self.app_state._refresh_if_needed()
            registry = RouteRegistry()
            if self.app_state.program is not None:
                refresh_routes(program=self.app_state.program, registry=registry, revision=self.app_state.revision, logger=print)
            server.route_registry = registry  # type: ignore[attr-defined]
            self.server = server
            startup_context = build_runtime_startup_context(
                app_path=self.app_path,
                bind_host="0.0.0.0",
                bind_port=self.port,
                mode=self.target or "service",
                headless=self.headless,
                manifest_payload=self.app_state.manifest_payload(),
                lock_path=self._port_lease.lock_path if self._port_lease is not None else None,
                lock_pid=self._port_lease.owner_pid if self._port_lease is not None else int(os.getpid()),
                validate_registry=not self.headless,
                enforce_parity=not self.headless,
            )
            print_startup_banner(startup_context)
            if background:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self._thread = thread
                self._serve_started = True
            else:
                self._serve_started = True
                server.serve_forever()
        except Exception:
            self.shutdown()
            raise

    def shutdown(self) -> None:
        if self.server:
            try:
                if self._serve_started:
                    self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        release_runtime_port_lock(self._port_lease)
        self._port_lease = None
        self._serve_started = False
        self.server = None

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
