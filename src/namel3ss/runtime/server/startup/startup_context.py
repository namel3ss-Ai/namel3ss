from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.ui.renderer.manifest_parity_guard import require_renderer_manifest_parity
from namel3ss.runtime.server.headless_api import build_manifest_hash
from namel3ss.studio.renderer_registry.manifest_loader import load_renderer_manifest_json
from namel3ss.studio.startup import validate_renderer_registry_startup
from namel3ss.ui.manifest import build_manifest


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
        payload = build_manifest(
            program,
            state={},
            display_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "build_program_manifest_payload",
    "RuntimeStartupContext",
    "build_runtime_startup_context",
    "resolve_renderer_registry_fingerprint",
]
