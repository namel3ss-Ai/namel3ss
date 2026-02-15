from __future__ import annotations

from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import threading

from namel3ss.diagnostics_mode import parse_diagnostics_flag
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_payload
from namel3ss.media import MediaValidationMode
from namel3ss.module_loader import load_project
from namel3ss.module_loader.source_io import ParseCache
from namel3ss.runtime.browser_state import record_data_effects, record_rows_snapshot, records_snapshot
from namel3ss.runtime.answer.traces import extract_answer_explain
from namel3ss.runtime.capabilities.contract_fields import attach_capability_manifest_fields
from namel3ss.runtime.dev_overlay import build_dev_overlay_payload
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.auth.identity_model import normalize_identity
from namel3ss.runtime.audit.runtime_capture import attach_audit_artifacts
from namel3ss.runtime.errors.normalize import attach_runtime_error_payload, merge_runtime_errors
from namel3ss.runtime.providers.guardrails import provider_guardrail_diagnostics
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.studio.session import SessionState
from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.elements.audit_viewer import inject_audit_viewer_elements
from namel3ss.ui.manifest.elements.runtime_error import inject_runtime_error_elements
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_PRODUCTION, DISPLAY_MODE_STUDIO, normalize_display_mode
from namel3ss.ui.settings import UI_ALLOWED_VALUES, UI_DEFAULTS
from namel3ss.validation import ValidationMode, ValidationWarning
from namel3ss.runtime.server.dev.errors import error_from_exception

def _locked(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper

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
        ui_mode: str | None = None,
        diagnostics_enabled: bool | None = None,
    ) -> None:
        self.app_path = Path(app_path).resolve()
        self.project_root = self.app_path.parent
        self.mode = mode
        self.debug = debug
        default_ui_mode = DISPLAY_MODE_PRODUCTION if mode in {"run", "preview"} else DISPLAY_MODE_STUDIO
        self.ui_mode = normalize_display_mode(ui_mode, default=default_ui_mode)
        env_diagnostics = parse_diagnostics_flag(os.getenv("N3_UI_DIAGNOSTICS"))
        self.diagnostics_enabled = env_diagnostics if diagnostics_enabled is None else bool(diagnostics_enabled)
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
        self._lock = threading.RLock()
        set_audit_root(self.project_root)
        set_engine_target(engine_target)

    @_locked
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
        runtime_errors = self._current_runtime_errors(config)
        cache_key = self._identity_cache_key(
            resolved_identity,
            auth_context=auth_context,
            runtime_errors=runtime_errors,
        )
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
            manifest, capability_errors = attach_capability_manifest_fields(
                manifest,
                program_ir=self.program,
                config=config,
            )
            runtime_errors = merge_runtime_errors(runtime_errors, capability_errors)
            if runtime_errors:
                inject_runtime_error_elements(manifest, runtime_errors)
            if warnings:
                manifest["warnings"] = [warning.to_dict() for warning in warnings]
            self.manifest_cache[cache_key] = manifest
            return manifest
        except Namel3ssError as err:
            payload = self._build_error_payload(err)
            self.manifest_errors[cache_key] = payload
            return payload

    @_locked
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

    @_locked
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

    @_locked
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
        guardrails = provider_guardrail_diagnostics(config) if self.ui_mode == DISPLAY_MODE_STUDIO else []
        response = {}
        identity_value = dict(identity) if isinstance(identity, dict) else None
        if identity_value is None:
            identity_value = resolve_identity(
                config,
                getattr(self.program, "identity", None),
                mode=ValidationMode.RUNTIME,
            )
        identity_value = normalize_identity(identity_value)
        cache_key = self._identity_cache_key(
            identity_value,
            auth_context=auth_context,
            runtime_errors=merge_runtime_errors(self.session.runtime_errors, guardrails),
        )
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
                ui_mode=self.ui_mode,
                diagnostics_enabled=self.diagnostics_enabled,
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
            response = error_from_exception(
                err,
                kind="engine",
                source=self._source_payload(),
                mode=self.mode,
                debug=self.debug,
            )
            response = attach_runtime_error_payload(
                response,
                status_code=400,
                endpoint="/api/action",
                diagnostics=guardrails,
            )
        except Exception as err:  # pragma: no cover - defensive guard
            response = build_error_payload(str(err), kind="internal")
            if self.mode == "dev":
                response["overlay"] = build_dev_overlay_payload(response, debug=self.debug)
            response = attach_runtime_error_payload(
                response,
                status_code=500,
                endpoint="/api/action",
                diagnostics=guardrails,
            )
        if isinstance(response, dict):
            response = attach_runtime_error_payload(
                response,
                status_code=None,
                endpoint="/api/action",
                diagnostics=guardrails,
            )
            response = attach_audit_artifacts(
                response,
                program_ir=self.program,
                config=config,
                action_id=action_id,
                input_payload=payload,
                state_snapshot=response.get("state") if isinstance(response.get("state"), dict) else self.session.state,
                source=self._main_source(),
                endpoint="/api/action",
            )
            runtime_errors = response.get("runtime_errors")
            if isinstance(runtime_errors, list):
                self.session.runtime_errors = runtime_errors
            else:
                self.session.runtime_errors = []
            if runtime_errors:
                refreshed_manifest = self._build_manifest(
                    self.program,
                    config=config,
                    identity=identity_value,
                    warnings=[],
                    auth_context=auth_context,
                )
                refreshed_manifest, capability_errors = attach_capability_manifest_fields(
                    refreshed_manifest,
                    program_ir=self.program,
                    config=config,
                )
                runtime_errors = merge_runtime_errors(runtime_errors, capability_errors)
                inject_runtime_error_elements(refreshed_manifest, runtime_errors)
                response["ui"] = refreshed_manifest
        ui_payload = response.get("ui") if isinstance(response, dict) else None
        if isinstance(ui_payload, dict):
            ui_mode = str(ui_payload.get("mode") or "").strip().lower()
            if ui_mode == DISPLAY_MODE_STUDIO:
                inject_audit_viewer_elements(
                    ui_payload,
                    run_artifact=response.get("run_artifact"),
                    audit_bundle=response.get("audit_bundle"),
                    audit_policy_status=response.get("audit_policy_status"),
                )
            resolved_cache_key = self._identity_cache_key(
                identity_value,
                auth_context=auth_context,
                runtime_errors=response.get("runtime_errors") if isinstance(response, dict) else None,
            )
            self.manifest_cache[resolved_cache_key] = ui_payload
            self.manifest_errors.pop(cache_key, None)
            theme_current = (ui_payload.get("theme") or {}).get("current")
            if isinstance(theme_current, str) and theme_current:
                self.session.runtime_theme = theme_current
        if isinstance(response, dict):
            if isinstance(response.get("state"), dict):
                self.session.state = response["state"]
        if isinstance(response, dict):
            explain = extract_answer_explain(response.get("traces"))
            if explain is not None:
                self.session.last_answer_explain = explain
        if isinstance(response, dict):
            response["state"] = self._state_snapshot()
            response.setdefault("revision", self.revision)
            return response
        return {"ok": False, "error": "Action failed.", "state": self._state_snapshot(), "revision": self.revision}

    @_locked
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
            self.session.runtime_errors = []
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
            display_mode=self.ui_mode,
            diagnostics_enabled=self.diagnostics_enabled,
        )
        return manifest

    def _identity_cache_key(
        self,
        identity: dict | None,
        auth_context: object | None = None,
        runtime_errors: list[dict[str, str]] | None = None,
    ) -> str:
        normalized = normalize_identity(identity if isinstance(identity, dict) else {})
        payload_map: dict[str, object] = {"identity": normalized}
        if auth_context is not None:
            error = getattr(auth_context, "error", None)
            authenticated = getattr(auth_context, "authenticated", None)
            if error is not None:
                payload_map["auth_error"] = error
            if isinstance(authenticated, bool):
                payload_map["authenticated"] = authenticated
        if isinstance(runtime_errors, list) and runtime_errors:
            payload_map["runtime_errors"] = runtime_errors
        payload = canonical_json_dumps(payload_map, pretty=False, drop_run_keys=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest[:12]

    def _current_runtime_errors(self, config) -> list[dict[str, str]]:
        guardrails = provider_guardrail_diagnostics(config) if self.ui_mode == DISPLAY_MODE_STUDIO else []
        return merge_runtime_errors(self.session.runtime_errors, guardrails)

    def _build_error_payload(self, err: Namel3ssError) -> dict:
        return error_from_exception(
            err,
            kind="manifest",
            source=self._source_payload(),
            mode=self.mode,
            debug=self.debug,
        )

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
__all__ = ["BrowserAppState"]
