from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.media import MediaValidationMode
from namel3ss.module_loader import load_project
from namel3ss.module_loader.source_io import ParseCache
from namel3ss.resources import studio_web_root
from namel3ss.runtime.dev_overlay import build_dev_overlay_payload
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.studio.session import SessionState
from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.settings import UI_ALLOWED_VALUES, UI_DEFAULTS
from namel3ss.ui.external.serve import resolve_external_ui_file
from namel3ss.validation import ValidationMode, ValidationWarning


DEFAULT_BROWSER_PORT = 7340


class BrowserRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
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
                payload = build_error_payload("Invalid JSON body.", kind="engine")
                self._respond_json(payload, status=400)
                return
            self._handle_action_post(body)
            return
        self.send_error(404)

    def _handle_api_get(self, path: str) -> None:
        if path == "/api/ui":
            payload = self._state().manifest_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/state":
            payload = self._state().state_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/dev/status":
            payload = self._state().status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/health":
            self._respond_json({"ok": True, "status": "ready", "mode": self._mode()})
            return
        self.send_error(404)

    def _handle_action_post(self, body: dict) -> None:
        if not isinstance(body, dict):
            self._respond_json(build_error_payload("Body must be a JSON object.", kind="engine"), status=400)
            return
        action_id = body.get("id")
        payload = body.get("payload") or {}
        if not isinstance(action_id, str):
            self._respond_json(build_error_payload("Action id is required.", kind="engine"), status=400)
            return
        if not isinstance(payload, dict):
            self._respond_json(build_error_payload("Payload must be an object.", kind="engine"), status=400)
            return
        response = self._state().run_action(action_id, payload)
        status = 200 if response.get("ok", True) else 400
        self._respond_json(response, status=status)

    def _handle_static(self, path: str) -> bool:
        file_path, content_type = _resolve_runtime_file(path, self._mode())
        if not file_path or not content_type:
            return False
        try:
            content = file_path.read_bytes()
        except OSError:  # pragma: no cover - IO guard
            return False
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def _respond_json(self, payload: dict, status: int = 200) -> None:
        data = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        if not raw_body:
            return {}
        try:
            decoded = raw_body.decode("utf-8")
            return json.loads(decoded or "{}")
        except Exception:
            return None

    def _state(self) -> "BrowserAppState":
        return self.server.app_state  # type: ignore[attr-defined]

    def _mode(self) -> str:
        return self.server.browser_mode  # type: ignore[attr-defined]


class BrowserAppState:
    def __init__(
        self,
        app_path: Path,
        *,
        mode: str,
        debug: bool,
        source_overrides: dict[Path, str] | None = None,
        watch_sources: bool = True,
        engine_target: str = "local",
    ) -> None:
        self.app_path = Path(app_path).resolve()
        self.project_root = self.app_path.parent
        self.mode = mode
        self.debug = debug
        self.source_overrides = source_overrides or {}
        self.watch_sources = watch_sources
        self.parse_cache: ParseCache = {}
        self.session = SessionState()
        self.program = None
        self.sources: dict[Path, str] = {}
        self.manifest: dict | None = None
        self.error_payload: dict | None = None
        self.revision = ""
        self._watch_snapshot: dict[Path, tuple[int, int]] = {}
        set_audit_root(self.project_root)
        set_engine_target(engine_target)

    def manifest_payload(self) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            return self.error_payload
        return self.manifest or {}

    def state_payload(self) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            return {"ok": False, "error": self.error_payload, "revision": self.revision}
        return {"ok": True, "state": self._state_snapshot(), "revision": self.revision}

    def status_payload(self) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            payload = {
                "ok": False,
                "revision": self.revision,
                "error": self.error_payload,
                "overlay": self.error_payload.get("overlay") if isinstance(self.error_payload, dict) else None,
            }
            return payload
        return {"ok": True, "revision": self.revision}

    def run_action(self, action_id: str, payload: dict) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            return self.error_payload
        if self.program is None:
            return build_error_payload("Program is not loaded.", kind="engine")
        config = load_config(app_path=self.app_path)
        store = self.session.ensure_store(config)
        runtime_theme = self.session.runtime_theme or getattr(self.program, "theme", UI_DEFAULTS["theme"])
        preference = getattr(self.program, "theme_preference", {}) or {}
        response = {}
        try:
            response = handle_action(
                self.program,
                action_id=action_id,
                payload=payload,
                state=self.session.state,
                store=store,
                runtime_theme=runtime_theme,
                preference_store=preference_store_for_app(self.app_path.as_posix(), preference.get("persist")),
                preference_key=app_pref_key(self.app_path.as_posix()),
                allow_theme_override=bool(preference.get("allow_override", False)),
                config=config,
                memory_manager=self.session.memory_manager,
                source=self._main_source(),
                raise_on_error=False,
            )
        except Namel3ssError as err:
            response = build_error_from_exception(err, kind="engine", source=self._source_payload())
            if self.mode == "dev":
                response["overlay"] = build_dev_overlay_payload(response, debug=self.debug)
        except Exception as err:  # pragma: no cover - defensive guard
            response = build_error_payload(str(err), kind="internal")
            if self.mode == "dev":
                response["overlay"] = build_dev_overlay_payload(response, debug=self.debug)
        ui_payload = response.get("ui") if isinstance(response, dict) else None
        if isinstance(ui_payload, dict):
            self.manifest = ui_payload
            theme_current = (ui_payload.get("theme") or {}).get("current")
            if isinstance(theme_current, str) and theme_current:
                self.session.runtime_theme = theme_current
        if isinstance(response, dict):
            if isinstance(response.get("state"), dict):
                self.session.state = response["state"]
        if isinstance(response, dict):
            response["state"] = self._state_snapshot()
            response.setdefault("revision", self.revision)
            return response
        return {"ok": False, "error": "Action failed.", "state": self._state_snapshot(), "revision": self.revision}

    def _refresh_if_needed(self) -> None:
        if not self._should_reload():
            return
        try:
            program, sources = self._load_program()
            self.program = program
            self.sources = sources
            self.revision = _compute_revision(sources)
            self._watch_snapshot = _snapshot_paths(list(sources.keys()))
            self.manifest = self._build_manifest(program)
            self.error_payload = None
        except Namel3ssError as err:
            self.error_payload = self._build_error_payload(err)
        except Exception as err:  # pragma: no cover - defensive guard
            self.error_payload = build_error_payload(str(err), kind="internal")
            if self.mode == "dev":
                self.error_payload["overlay"] = build_dev_overlay_payload(self.error_payload, debug=self.debug)

    def _should_reload(self) -> bool:
        if not self.watch_sources:
            return self.program is None
        watch_paths = self._watch_paths()
        snapshot = _snapshot_paths(watch_paths)
        if not self._watch_snapshot:
            self._watch_snapshot = snapshot
            return True
        if snapshot != self._watch_snapshot:
            self._watch_snapshot = snapshot
            return True
        return False

    def _watch_paths(self) -> list[Path]:
        if not self.watch_sources:
            return []
        if self.sources:
            return sorted(self.sources.keys(), key=lambda p: p.as_posix())
        return _scan_project_sources(self.project_root)

    def _load_program(self) -> tuple[object, dict[Path, str]]:
        apply_dotenv(load_dotenv_for_path(str(self.app_path)))
        project = load_project(self.app_path, parse_cache=self.parse_cache, source_overrides=self.source_overrides)
        return project.program, project.sources

    def _build_manifest(self, program) -> dict:
        config = load_config(app_path=self.app_path)
        warnings: list[ValidationWarning] = []
        store = self.session.ensure_store(config)
        preference = getattr(program, "theme_preference", {}) or {}
        preference_store = preference_store_for_app(self.app_path.as_posix(), preference.get("persist"))
        preference_key = app_pref_key(self.app_path.as_posix())
        persisted, _ = preference_store.load_theme(preference_key)
        allowed_themes = set(UI_ALLOWED_VALUES.get("theme", ()))
        program_theme = getattr(program, "theme", UI_DEFAULTS["theme"])
        runtime_theme = self.session.runtime_theme or persisted or program_theme
        if runtime_theme not in allowed_themes:
            runtime_theme = program_theme if program_theme in allowed_themes else UI_DEFAULTS["theme"]
        self.session.runtime_theme = runtime_theme
        identity = resolve_identity(config, getattr(program, "identity", None), mode=ValidationMode.RUNTIME, warnings=warnings)
        manifest = build_manifest(
            program,
            config=config,
            state=self.session.state,
            store=resolve_store(store, config=config),
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
            identity=identity,
            mode=ValidationMode.RUNTIME,
            warnings=warnings,
            media_mode=MediaValidationMode.CHECK,
        )
        if warnings:
            manifest["warnings"] = [warning.to_dict() for warning in warnings]
        return manifest

    def _build_error_payload(self, err: Namel3ssError) -> dict:
        payload = build_error_from_exception(err, kind="manifest", source=self._source_payload())
        if self.mode == "dev":
            payload["overlay"] = build_dev_overlay_payload(payload, debug=self.debug)
        return payload

    def _source_payload(self) -> dict:
        if self.sources:
            return dict(self.sources)
        return _read_source_fallback(self.app_path)

    def _main_source(self) -> str | None:
        if self.sources and self.app_path in self.sources:
            return self.sources[self.app_path]
        try:
            return self.app_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _state_snapshot(self) -> dict:
        try:
            return json.loads(canonical_json_dumps(self.session.state, pretty=False, drop_run_keys=False))
        except Exception:
            return {}


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


def _resolve_runtime_file(path: str, mode: str) -> tuple[Path | None, str | None]:
    runtime_root = _runtime_web_root()
    if path in {"/", "/index.html"}:
        filename = "dev.html" if mode == "dev" else "preview.html"
        if mode == "run":
            filename = "preview.html"
        file_path = runtime_root / filename
        if file_path.exists():
            return file_path, "text/html"
    for root in (runtime_root, studio_web_root()):
        file_path, content_type = resolve_external_ui_file(root, path)
        if file_path and content_type:
            return file_path, content_type
    return None, None


def _runtime_web_root() -> Path:
    return Path(__file__).resolve().parent / "web"


def _scan_project_sources(project_root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(project_root.rglob("*.ai"), key=lambda p: p.as_posix()):
        if ".namel3ss" in path.parts:
            continue
        paths.append(path)
    return paths or [project_root / "app.ai"]


def _snapshot_paths(paths: list[Path]) -> dict[Path, tuple[int, int]]:
    snapshot: dict[Path, tuple[int, int]] = {}
    for path in paths:
        try:
            stat = path.stat()
            snapshot[path] = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            snapshot[path] = (-1, -1)
    return snapshot


def _compute_revision(sources: dict[Path, str]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(text.encode("utf-8"))
    return digest.hexdigest()[:12]


def _read_source_fallback(app_path: Path) -> dict[Path, str]:
    try:
        return {app_path: app_path.read_text(encoding="utf-8")}
    except OSError:
        return {}


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


__all__ = ["BrowserRunner", "BrowserAppState", "DEFAULT_BROWSER_PORT"]
