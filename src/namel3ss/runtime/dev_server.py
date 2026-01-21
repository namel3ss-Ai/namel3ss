from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.media import MediaValidationMode
from namel3ss.module_loader import load_project
from namel3ss.module_loader.source_io import ParseCache
from namel3ss.resources import studio_web_root
from namel3ss.runtime.browser_state import record_data_effects, record_rows_snapshot, records_snapshot
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)
from namel3ss.runtime.dev_overlay import build_dev_overlay_payload
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.identity_model import normalize_identity
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.backend.upload_handler import handle_upload, handle_upload_list
from namel3ss.runtime.observability_api import (
    get_logs_payload,
    get_metrics_payload,
    get_trace_payload,
    get_traces_payload,
)
from namel3ss.runtime.deploy_routes import get_build_payload, get_deploy_payload
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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/action":
            body = self._read_json_body()
            if body is None:
                payload = build_error_payload("Invalid JSON body.", kind="engine")
                self._respond_json(payload, status=400)
                return
            self._handle_action_post(body)
            return
        if path == "/api/login":
            body = self._read_json_body()
            if body is None:
                payload = build_error_payload("Invalid JSON body.", kind="authentication")
                self._respond_json(payload, status=400)
                return
            payload, status, headers = self._handle_login_post(body)
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/logout":
            payload, status, headers = self._handle_logout_post()
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/upload":
            response, status = self._handle_upload_post(parsed.query)
            self._respond_json(response, status=status)
            return
        self.send_error(404)

    def _handle_api_get(self, path: str) -> None:
        if path == "/api/session":
            payload, status, headers = self._handle_session_get()
            self._respond_json(payload, status=status, headers=headers)
            return
        if path == "/api/ui":
            auth_context = self._auth_context_or_error(kind="manifest")
            if auth_context is None:
                return
            payload = self._state().manifest_payload(identity=auth_context.identity, auth_context=auth_context)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/state":
            auth_context = self._auth_context_or_error(kind="state")
            if auth_context is None:
                return
            payload = self._state().state_payload(identity=auth_context.identity)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/data/status":
            payload = self._data_status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/migrations/status":
            payload = self._migrations_status_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/migrations/plan":
            payload = self._migrations_plan_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/uploads":
            response, status = self._handle_upload_list()
            self._respond_json(response, status=status)
            return
        if path == "/api/logs":
            payload = self._observability_payload(get_logs_payload)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/traces":
            payload = self._observability_payload(get_traces_payload)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/trace":
            payload = self._observability_payload(get_trace_payload)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/metrics":
            payload = self._observability_payload(get_metrics_payload)
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/build":
            payload = self._build_payload()
            status = 200 if payload.get("ok", True) else 400
            self._respond_json(payload, status=status)
            return
        if path == "/api/deploy":
            payload = self._deploy_payload()
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
        auth_context = self._auth_context_or_error(kind="engine")
        if auth_context is None:
            return
        response = self._state().run_action(
            action_id,
            payload,
            identity=auth_context.identity,
            auth_context=auth_context,
        )
        status = 200 if response.get("ok", True) else 400
        self._respond_json(response, status=status)

    def _handle_upload_post(self, query: str) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            payload = build_error_payload("Program not loaded.", kind="engine")
            return payload, 500
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
            capabilities=getattr(program, "capabilities", ()),
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        try:
            response = handle_upload(
                ctx,
                headers=dict(self.headers.items()),
                rfile=self.rfile,
                content_length=content_length,
                upload_name=upload_name,
            )
            return response, 200
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine", source=self._source_payload())
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=self._state().debug)
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard
            payload = build_error_payload(str(err), kind="internal")
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=self._state().debug)
            return payload, 500

    def _handle_upload_list(self) -> tuple[dict, int]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            payload = build_error_payload("Program not loaded.", kind="engine")
            return payload, 500
        ctx = SimpleNamespace(
            capabilities=getattr(program, "capabilities", ()),
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        try:
            response = handle_upload_list(ctx)
            return response, 200
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="engine", source=self._source_payload())
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=self._state().debug)
            return payload, 400
        except Exception as err:  # pragma: no cover - defensive guard
            payload = build_error_payload(str(err), kind="internal")
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=self._state().debug)
            return payload, 500

    def _observability_payload(self, builder) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine")
        return builder(getattr(program, "project_root", None), getattr(program, "app_path", None))

    def _build_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        return get_build_payload(root, app_path)

    def _deploy_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        root = getattr(program, "project_root", None) if program is not None else state.project_root
        app_path = getattr(program, "app_path", None) if program is not None else state.app_path
        return get_deploy_payload(root, app_path, program=program)

    def _data_status_payload(self) -> dict:
        state = self._state()
        state._refresh_if_needed()
        try:
            config = load_config(app_path=state.app_path)
            return build_data_status_payload(
                config,
                project_root=state.project_root,
                app_path=state.app_path,
            )
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="data", source=state._source_payload())
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=state.debug)
            return payload
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=state.debug)
            return payload

    def _migrations_status_payload(self) -> dict:
        return self._migrations_payload(build_migrations_status_payload)

    def _migrations_plan_payload(self) -> dict:
        return self._migrations_payload(build_migrations_plan_payload)

    def _migrations_payload(self, builder) -> dict:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        if program is None:
            return build_error_payload("Program not loaded.", kind="engine")
        try:
            return builder(program, project_root=state.project_root)
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind="data", source=state._source_payload())
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=state.debug)
            return payload
        except Exception as err:  # pragma: no cover - defensive guard rail
            payload = build_error_payload(str(err), kind="internal")
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=state.debug)
            return payload

    def _auth_params(self) -> tuple[object, object | None, object]:
        state = self._state()
        state._refresh_if_needed()
        program = state.program
        config = load_config(app_path=state.app_path)
        store = state.session.ensure_store(config)
        identity_schema = getattr(program, "identity", None) if program is not None else None
        return config, identity_schema, store

    def _handle_session_get(self) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_session(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _handle_login_post(self, body: dict) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_login(
            dict(self.headers.items()),
            body,
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _handle_logout_post(self) -> tuple[dict, int, dict[str, str]]:
        try:
            config, identity_schema, store = self._auth_params()
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
        return handle_logout(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _resolve_auth_context(self) -> object:
        config, identity_schema, store = self._auth_params()
        return resolve_auth_context(
            dict(self.headers.items()),
            config=config,
            identity_schema=identity_schema,
            store=store,
        )

    def _auth_context_or_error(self, *, kind: str) -> object | None:
        try:
            return self._resolve_auth_context()
        except Namel3ssError as err:
            payload = build_error_from_exception(err, kind=kind, source=self._state()._source_payload())
            if self._mode() == "dev":
                payload["overlay"] = build_dev_overlay_payload(payload, debug=self._state().debug)
            self._respond_json(payload, status=400)
            return None

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

    def _respond_json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        data = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
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
        self.manifest_cache: dict[str, dict] = {}
        self.manifest_errors: dict[str, dict] = {}
        self.error_payload: dict | None = None
        self.revision = ""
        self._watch_snapshot: dict[Path, tuple[int, int]] = {}
        set_audit_root(self.project_root)
        set_engine_target(engine_target)

    def manifest_payload(self, *, identity: dict | None = None, auth_context: object | None = None) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            return self.error_payload
        if self.program is None:
            return {}
        config = load_config(app_path=self.app_path)
        warnings: list[ValidationWarning] = []
        resolved_identity = dict(identity) if isinstance(identity, dict) else None
        if resolved_identity is None:
            resolved_identity = resolve_identity(
                config,
                getattr(self.program, "identity", None),
                mode=ValidationMode.RUNTIME,
                warnings=warnings,
            )
        resolved_identity = normalize_identity(resolved_identity)
        cache_key = self._identity_cache_key(resolved_identity, auth_context=auth_context)
        cached = self.manifest_cache.get(cache_key)
        if cached is not None:
            return cached
        cached_error = self.manifest_errors.get(cache_key)
        if cached_error is not None:
            return cached_error
        try:
            manifest = self._build_manifest(
                self.program,
                config=config,
                identity=resolved_identity,
                warnings=warnings,
                auth_context=auth_context,
            )
            if warnings:
                manifest["warnings"] = [warning.to_dict() for warning in warnings]
            self.manifest_cache[cache_key] = manifest
            return manifest
        except Namel3ssError as err:
            payload = self._build_error_payload(err)
            self.manifest_errors[cache_key] = payload
            return payload

    def state_payload(self, *, identity: dict | None = None) -> dict:
        self._refresh_if_needed()
        if self.error_payload:
            return {"ok": False, "error": self.error_payload, "revision": self.revision}
        records = []
        if self.program is not None:
            config = load_config(app_path=self.app_path)
            store = self.session.ensure_store(config)
            records = records_snapshot(self.program, store, config, identity=identity)
        payload = {
            "ok": True,
            "state": self._state_snapshot(),
            "records": records,
            "revision": self.revision,
        }
        if self.session.data_effects:
            payload["effects"] = self.session.data_effects
        return payload

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

    def run_action(
        self,
        action_id: str,
        payload: dict,
        *,
        identity: dict | None = None,
        auth_context: object | None = None,
    ) -> dict:
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
        identity_value = dict(identity) if isinstance(identity, dict) else None
        if identity_value is None:
            identity_value = resolve_identity(
                config,
                getattr(self.program, "identity", None),
                mode=ValidationMode.RUNTIME,
            )
        identity_value = normalize_identity(identity_value)
        cache_key = self._identity_cache_key(identity_value, auth_context=auth_context)
        try:
            before_rows = None
            if self.program is not None:
                before_rows = record_rows_snapshot(self.program, store, config, identity=identity_value)
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
                identity=identity_value,
                auth_context=auth_context,
                memory_manager=self.session.memory_manager,
                source=self._main_source(),
                raise_on_error=False,
            )
            if before_rows is not None:
                self.session.data_effects = record_data_effects(
                    self.program,
                    store,
                    config,
                    action_id,
                    response,
                    before_rows,
                    identity=identity_value,
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
            self.manifest_cache[cache_key] = ui_payload
            self.manifest_errors.pop(cache_key, None)
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
            self.manifest_cache = {}
            self.manifest_errors = {}
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

    def _build_manifest(
        self,
        program,
        *,
        config,
        identity: dict,
        warnings: list[ValidationWarning],
        auth_context: object | None = None,
    ) -> dict:
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
        manifest = build_manifest(
            program,
            config=config,
            state=self.session.state,
            store=resolve_store(store, config=config),
            runtime_theme=runtime_theme,
            persisted_theme=persisted,
            identity=identity,
            auth_context=auth_context,
            mode=ValidationMode.RUNTIME,
            warnings=warnings,
            media_mode=MediaValidationMode.CHECK,
        )
        return manifest

    def _identity_cache_key(self, identity: dict | None, auth_context: object | None = None) -> str:
        normalized = normalize_identity(identity if isinstance(identity, dict) else {})
        payload_map: dict[str, object] = {"identity": normalized}
        if auth_context is not None:
            error = getattr(auth_context, "error", None)
            authenticated = getattr(auth_context, "authenticated", None)
            if error is not None:
                payload_map["auth_error"] = error
            if isinstance(authenticated, bool):
                payload_map["authenticated"] = authenticated
        payload = canonical_json_dumps(payload_map, pretty=False, drop_run_keys=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest[:12]

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
