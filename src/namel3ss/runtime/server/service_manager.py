from __future__ import annotations

import os
import threading
from http.server import HTTPServer
from pathlib import Path

from namel3ss.diagnostics_mode import parse_diagnostics_flag
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.runtime.performance.config import normalize_performance_runtime_config
from namel3ss.runtime.performance.guard import require_performance_capability
from namel3ss.runtime.lifecycle.hooks import run_shutdown_hooks, run_startup_hooks
from namel3ss.runtime.router.program_state import ProgramState
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.security.retention_loop import run_retention_loop
from namel3ss.runtime.server.cluster_control import ClusterControlPlane
from namel3ss.runtime.server.concurrency import create_runtime_http_server, load_concurrency_config
from namel3ss.runtime.server.headless_api import normalize_api_token, normalize_cors_origins
from namel3ss.runtime.server.handlers import ServiceRequestHandler
from namel3ss.runtime.server.lock import (
    RuntimePortLease,
    acquire_runtime_port_lock,
    release_runtime_port_lock,
)
from namel3ss.runtime.server.startup import (
    build_program_manifest_payload,
    build_runtime_startup_context,
    print_startup_banner,
    require_static_runtime_manifest_parity,
)
from namel3ss.runtime.server.session_manager import DEFAULT_IDLE_TIMEOUT_SECONDS, ServiceSessionManager
from namel3ss.runtime.server.service_process_model import configure_server_process_model
from namel3ss.runtime.server.worker_pool import ServiceActionWorkerPool
from namel3ss.runtime.service_helpers import seed_flow, should_auto_seed, summarize_program
from namel3ss.runtime.triggers import run_service_trigger_loop
from namel3ss.runtime.storage.factory import create_store
from namel3ss.ui.external.detect import resolve_external_ui_root
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_PRODUCTION, normalize_display_mode

DEFAULT_SERVICE_PORT = 8787


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
        headless: bool = False,
        headless_api_token: str | None = None,
        headless_cors_origins: tuple[str, ...] | None = None,
        ui_mode: str | None = None,
        require_service_capability: bool = False,
    ):
        self.app_path = Path(app_path).resolve()
        self.target = target
        self.build_id = build_id
        self.port = port or DEFAULT_SERVICE_PORT
        self.auto_seed = auto_seed
        self.seed_flow = seed_flow
        self.headless = headless
        self.headless_api_token = normalize_api_token(headless_api_token or os.getenv("N3_HEADLESS_API_TOKEN"))
        if headless_cors_origins:
            self.headless_cors_origins = normalize_cors_origins(headless_cors_origins)
        else:
            self.headless_cors_origins = normalize_cors_origins(os.getenv("N3_HEADLESS_CORS_ORIGINS"))
        self.require_service_capability = bool(require_service_capability)
        env_mode = os.getenv("N3_UI_MODE")
        chosen_ui_mode = ui_mode if ui_mode is not None else env_mode
        self.ui_mode = normalize_display_mode(chosen_ui_mode, default=DISPLAY_MODE_PRODUCTION)
        self.diagnostics_enabled = parse_diagnostics_flag(os.getenv("N3_UI_DIAGNOSTICS"))
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._trigger_thread: threading.Thread | None = None
        self._trigger_stop = threading.Event()
        self._retention_thread: threading.Thread | None = None
        self._retention_stop = threading.Event()
        self._worker_pool: ServiceActionWorkerPool | None = None
        self._cluster_control: ClusterControlPlane | None = None
        self._lifecycle_snapshot = None
        self._port_lease: RuntimePortLease | None = None
        self._serve_started = False
        self.program_summary: dict[str, object] = {}
        self.concurrency = load_concurrency_config(app_path=self.app_path)

    def start(self, *, background: bool = False) -> None:
        program_state = ProgramState(self.app_path)
        program_ir = program_state.program
        if program_ir is None:
            raise Namel3ssError("Program failed to load.")
        capabilities = _normalized_capabilities(getattr(program_ir, "capabilities", ()))
        has_service_capability = "service" in capabilities
        if self.require_service_capability and not has_service_capability:
            raise Namel3ssError(_missing_service_capability_message())
        allow_multi_user = "multi_user" in capabilities
        remote_studio_enabled = "remote_studio" in capabilities
        resolved_config = load_config(app_path=self.app_path, root=self.app_path.parent)
        self._lifecycle_snapshot = run_startup_hooks(
            target=self.target,
            program=program_ir,
            config=resolved_config,
            project_root=getattr(program_ir, "project_root", None),
            app_path=getattr(program_ir, "app_path", None),
            allow_pending_migrations=_allow_pending_migrations(),
            auto_migrate=_auto_migrate_enabled(),
            dry_run=False,
        )
        runtime_config = normalize_performance_runtime_config(resolved_config)
        require_performance_capability(
            getattr(program_ir, "capabilities", ()),
            runtime_config,
            where="runtime configuration",
        )
        self.program_summary = summarize_program(program_ir)
        if should_auto_seed(program_ir, self.auto_seed, self.seed_flow):
            seed_flow(program_ir, self.seed_flow)
        external_ui_root = resolve_external_ui_root(
            getattr(program_ir, "project_root", None),
            getattr(program_ir, "app_path", None),
        )
        self._port_lease = acquire_runtime_port_lock(
            host="0.0.0.0",
            port=self.port,
            app_path=self.app_path,
            mode="service",
            allow_reentrant=False,
        )
        try:
            server = create_runtime_http_server("0.0.0.0", self.port, ServiceRequestHandler, config=self.concurrency)
        except Exception:
            release_runtime_port_lock(self._port_lease)
            self._port_lease = None
            raise
        self.port = int(server.server_address[1])
        try:
            server.target = self.target  # type: ignore[attr-defined]
            server.build_id = self.build_id  # type: ignore[attr-defined]
            server.app_path = self.app_path.as_posix()  # type: ignore[attr-defined]
            self._worker_pool = configure_server_process_model(
                server=server,
                program_ir=program_ir,
                app_path=self.app_path,
                concurrency=self.concurrency,
                ui_mode=self.ui_mode,
                diagnostics_enabled=self.diagnostics_enabled,
            )
            server.concurrency = self.concurrency.to_dict()  # type: ignore[attr-defined]
            server.headless = self.headless  # type: ignore[attr-defined]
            server.headless_api_token = self.headless_api_token  # type: ignore[attr-defined]
            server.headless_cors_origins = self.headless_cors_origins  # type: ignore[attr-defined]
            server.program_summary = self.program_summary  # type: ignore[attr-defined]
            server.program_ir = program_ir  # type: ignore[attr-defined]
            server.program_state = program_state  # type: ignore[attr-defined]
            registry = RouteRegistry()
            refresh_routes(program=program_ir, registry=registry, revision=program_state.revision, logger=print)
            server.route_registry = registry  # type: ignore[attr-defined]
            server.external_ui_root = None if self.headless else external_ui_root  # type: ignore[attr-defined]
            server.external_ui_enabled = bool(not self.headless and external_ui_root is not None)  # type: ignore[attr-defined]
            server.ui_mode = self.ui_mode  # type: ignore[attr-defined]
            server.ui_diagnostics_enabled = self.diagnostics_enabled  # type: ignore[attr-defined]
            server.lifecycle = self._lifecycle_snapshot.as_dict() if self._lifecycle_snapshot is not None else None  # type: ignore[attr-defined]
            if has_service_capability:
                idle_timeout = _service_idle_timeout()
                base_store = create_store(config=resolved_config)
                server.session_manager = ServiceSessionManager(  # type: ignore[attr-defined]
                    base_store=base_store,
                    project_root=getattr(program_ir, "project_root", None),
                    app_path=getattr(program_ir, "app_path", None),
                    allow_multi_user=allow_multi_user,
                    remote_studio_enabled=remote_studio_enabled,
                    idle_timeout_seconds=idle_timeout,
                )
            else:
                server.session_manager = None  # type: ignore[attr-defined]
            startup_manifest_payload = build_program_manifest_payload(
                program=program_ir,
                ui_mode=self.ui_mode,
                diagnostics_enabled=self.diagnostics_enabled,
            )
            require_static_runtime_manifest_parity(
                program=program_ir,
                runtime_manifest_payload=startup_manifest_payload,
                static_manifest_payload=startup_manifest_payload,
                ui_mode=self.ui_mode,
                diagnostics_enabled=self.diagnostics_enabled,
            )
            startup_context = build_runtime_startup_context(
                app_path=self.app_path,
                bind_host="0.0.0.0",
                bind_port=self.port,
                mode="service",
                headless=self.headless,
                manifest_payload=startup_manifest_payload,
                lock_path=self._port_lease.lock_path if self._port_lease is not None else None,
                lock_pid=self._port_lease.owner_pid if self._port_lease is not None else int(os.getpid()),
                validate_registry=not self.headless,
                enforce_parity=not self.headless,
            )
            print_startup_banner(startup_context)
            self.server = server
            self._cluster_control = ClusterControlPlane(
                project_root=self.app_path.parent,
                app_path=self.app_path,
                worker_pool=self._worker_pool,
                server=server,
            )
            self._cluster_control.start()
            self._trigger_stop.clear()
            self._trigger_thread = threading.Thread(
                target=run_service_trigger_loop,
                kwargs={
                    "stop_event": self._trigger_stop,
                    "program_state": program_state,
                    "flow_store": getattr(server, "flow_store", None),
                },
                daemon=True,
            )
            self._trigger_thread.start()
            self._retention_stop.clear()
            self._retention_thread = threading.Thread(
                target=run_retention_loop,
                kwargs={"stop_event": self._retention_stop, "program_state": program_state},
                daemon=True,
            )
            self._retention_thread.start()
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
        self._trigger_stop.set()
        self._retention_stop.set()
        if self._cluster_control is not None:
            self._cluster_control.stop()
            self._cluster_control = None
        if self.server:
            try:
                if self._serve_started:
                    self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self._trigger_thread and self._trigger_thread.is_alive():
            self._trigger_thread.join(timeout=1)
        if self._retention_thread and self._retention_thread.is_alive():
            self._retention_thread.join(timeout=1)
        if self._worker_pool is not None:
            self._worker_pool.shutdown()
            self._worker_pool = None
        release_runtime_port_lock(self._port_lease)
        self._port_lease = None
        self._serve_started = False
        self.server = None
        run_shutdown_hooks(self._lifecycle_snapshot)
        self._lifecycle_snapshot = None

    @property
    def bound_port(self) -> int:
        return int(self.server.server_address[1]) if self.server else self.port


__all__ = ["DEFAULT_SERVICE_PORT", "ServiceRunner"]


def _normalized_capabilities(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    normalized: list[str] = []
    for value in values:
        token = normalize_builtin_capability(value if isinstance(value, str) else None)
        if token and token not in normalized:
            normalized.append(token)
    return tuple(normalized)


def _service_idle_timeout() -> int:
    raw = os.getenv("N3_SERVICE_IDLE_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    return max(0, value)


def _allow_pending_migrations() -> bool:
    token = os.getenv("N3_ALLOW_PENDING_MIGRATIONS", "true").strip().lower()
    return token in {"1", "true", "yes", "on"}


def _auto_migrate_enabled() -> bool:
    token = os.getenv("N3_AUTO_MIGRATE", "false").strip().lower()
    return token in {"1", "true", "yes", "on"}


def _missing_service_capability_message() -> str:
    return build_guidance_message(
        what='Capability "service" is required.',
        why="Service mode is opt-in and disabled by default.",
        fix="Add service to the app capabilities block and retry.",
        example='capabilities:\n  service',
    )
