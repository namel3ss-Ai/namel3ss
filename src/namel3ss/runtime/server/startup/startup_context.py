from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.contract_fields import attach_capability_manifest_fields
from namel3ss.runtime.errors.normalize import merge_runtime_errors
from namel3ss.runtime.providers.guardrails import provider_guardrail_diagnostics
from namel3ss.runtime.server.headless_api import build_manifest_hash
from namel3ss.runtime.ui.renderer.manifest_parity_guard import require_renderer_manifest_parity
from namel3ss.studio.renderer_registry.manifest_loader import load_renderer_manifest_json
from namel3ss.studio.startup import validate_renderer_registry_startup
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
from namel3ss.ui.manifest.elements.runtime_error import inject_runtime_error_elements
from namel3ss.validation_entrypoint import build_static_manifest


RUNTIME_MANIFEST_DRIFT_ERROR_CODE = "N3E_RUNTIME_MANIFEST_DRIFT"
_MANIFEST_PARITY_IGNORED_KEYS = {
    "audit_bundle",
    "audit_policy_status",
    "capabilities_enabled",
    "capability_versions",
    "migration_status",
    "persistence_backend",
    "run_artifact",
    "state_schema_version",
    "warnings",
}


@dataclass(frozen=True)
class RuntimeStartupContext:
    app_path: str
    bind_host: str
    bind_port: int
    mode: str
    headless: bool
    manifest_hash: str
    renderer_registry_hash: str
    renderer_registry_status: str
    lock_path: str
    lock_pid: int

    def to_dict(self) -> dict[str, object]:
        return {
            "app_path": self.app_path,
            "bind_host": self.bind_host,
            "bind_port": int(self.bind_port),
            "headless": bool(self.headless),
            "lock_path": self.lock_path,
            "lock_pid": int(self.lock_pid),
            "manifest_hash": self.manifest_hash,
            "mode": self.mode,
            "renderer_registry_hash": self.renderer_registry_hash,
            "renderer_registry_status": self.renderer_registry_status,
        }


def build_runtime_startup_context(
    *,
    app_path: Path,
    bind_host: str,
    bind_port: int,
    mode: str,
    headless: bool,
    manifest_payload: dict[str, Any] | None,
    lock_path: Path | None,
    lock_pid: int,
    validate_registry: bool = True,
    enforce_parity: bool = False,
) -> RuntimeStartupContext:
    manifest_data = manifest_payload if isinstance(manifest_payload, dict) else {}
    renderer_hash, renderer_status = resolve_renderer_registry_fingerprint(
        validate_registry=validate_registry,
        enforce_parity=enforce_parity,
    )
    return RuntimeStartupContext(
        app_path=Path(app_path).resolve().as_posix(),
        bind_host=str(bind_host).strip(),
        bind_port=int(bind_port),
        mode=str(mode or "").strip(),
        headless=bool(headless),
        manifest_hash=build_manifest_hash(manifest_data),
        renderer_registry_hash=renderer_hash,
        renderer_registry_status=renderer_status,
        lock_path=lock_path.as_posix() if isinstance(lock_path, Path) else "",
        lock_pid=int(lock_pid),
    )


def resolve_renderer_registry_fingerprint(
    *,
    validate_registry: bool,
    enforce_parity: bool = False,
) -> tuple[str, str]:
    status = "available"
    if validate_registry and enforce_parity:
        validate_renderer_registry_startup()
    if enforce_parity:
        require_renderer_manifest_parity()
    try:
        manifest_json = load_renderer_manifest_json()
        payload = canonical_json_dumps(manifest_json, pretty=False, drop_run_keys=False).encode("utf-8")
        manifest_hash = hashlib.sha256(payload).hexdigest()
    except Exception:
        if enforce_parity:
            raise
        return "", "unavailable"
    if validate_registry and not enforce_parity:
        try:
            validate_renderer_registry_startup()
            status = "validated"
        except Exception:
            status = "invalid"
    if validate_registry and enforce_parity:
        status = "validated"
    elif enforce_parity:
        status = "parity_validated"
    return manifest_hash, status


def build_program_manifest_payload(
    *,
    program: object,
    ui_mode: str,
    diagnostics_enabled: bool,
) -> dict[str, Any]:
    try:
        return build_static_startup_manifest_payload(
            program,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
    except Exception:
        return {}


def build_static_startup_manifest_payload(
    program: object,
    *,
    ui_mode: str,
    diagnostics_enabled: bool,
) -> dict[str, Any]:
    config = load_config(
        app_path=getattr(program, "app_path", None),
        root=getattr(program, "project_root", None),
    )
    warnings: list = []
    payload = build_static_manifest(
        program,
        config=config,
        state={},
        store=None,
        warnings=warnings,
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    manifest = payload if isinstance(payload, dict) else {}
    manifest, capability_errors = attach_capability_manifest_fields(
        manifest,
        program_ir=program,
        config=config,
    )
    runtime_errors = provider_guardrail_diagnostics(config) if ui_mode == DISPLAY_MODE_STUDIO else []
    runtime_errors = merge_runtime_errors(runtime_errors, capability_errors)
    if runtime_errors:
        inject_runtime_error_elements(manifest, runtime_errors)
    if warnings:
        manifest = dict(manifest)
        manifest["warnings"] = [warning.to_dict() for warning in warnings if hasattr(warning, "to_dict")]
    return manifest


def require_static_runtime_manifest_parity(
    *,
    program: object | None,
    runtime_manifest_payload: dict[str, Any] | None,
    ui_mode: str,
    diagnostics_enabled: bool,
    static_manifest_payload: dict[str, Any] | None = None,
) -> str:
    runtime_payload = runtime_manifest_payload if isinstance(runtime_manifest_payload, dict) else {}
    if not runtime_payload:
        return ""
    if runtime_payload.get("ok") is False:
        return ""
    if program is None:
        return ""
    static_payload = static_manifest_payload if isinstance(static_manifest_payload, dict) else None
    if static_payload is None:
        static_payload = build_static_startup_manifest_payload(
            program,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
    if not static_payload:
        return ""
    static_hash = _parity_hash(static_payload)
    runtime_hash = _parity_hash(runtime_payload)
    if static_hash == runtime_hash:
        return runtime_hash
    app_path = getattr(program, "app_path", None)
    app_token = Path(app_path).as_posix() if app_path else "app.ai"
    raise Namel3ssError(
        build_guidance_message(
            what=f"{RUNTIME_MANIFEST_DRIFT_ERROR_CODE}: startup manifest parity check failed.",
            why=f"n3 ui hash {static_hash} does not match runtime hash {runtime_hash}.",
            fix="Regenerate UI artifacts and run startup with the same app path and UI mode used for n3 ui.",
            example=f"n3 ui {app_token}",
        ),
        details={
            "category": "engine",
            "error_code": RUNTIME_MANIFEST_DRIFT_ERROR_CODE,
            "runtime_hash": runtime_hash,
            "static_hash": static_hash,
            "app_path": app_token,
            "ui_mode": str(ui_mode or "").strip(),
            "diagnostics_enabled": bool(diagnostics_enabled),
        },
    )


def _parity_hash(payload: dict[str, Any]) -> str:
    return build_manifest_hash(_normalize_manifest_for_parity(payload))


def _normalize_manifest_for_parity(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _MANIFEST_PARITY_IGNORED_KEYS:
            continue
        normalized[key] = value
    return normalized


__all__ = [
    "build_static_startup_manifest_payload",
    "build_program_manifest_payload",
    "require_static_runtime_manifest_parity",
    "RUNTIME_MANIFEST_DRIFT_ERROR_CODE",
    "RuntimeStartupContext",
    "build_runtime_startup_context",
    "resolve_renderer_registry_fingerprint",
]
