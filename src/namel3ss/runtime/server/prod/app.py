from __future__ import annotations

import threading
from http.server import HTTPServer
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.dev_server import BrowserAppState
from namel3ss.runtime.server.prod.routes import ProductionRequestHandler
from namel3ss.runtime.router.refresh import refresh_routes
from namel3ss.runtime.router.registry import RouteRegistry


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
        self.app_state._refresh_if_needed()
        registry = RouteRegistry()
        if self.app_state.program is not None:
            refresh_routes(program=self.app_state.program, registry=registry, revision=self.app_state.revision, logger=print)
        server.route_registry = registry  # type: ignore[attr-defined]
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
