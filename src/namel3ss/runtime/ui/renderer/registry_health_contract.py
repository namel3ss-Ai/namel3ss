from __future__ import annotations

from namel3ss.runtime.ui.renderer.manifest_parity_guard import verify_renderer_manifest_parity
from namel3ss.runtime.ui.renderer.registry_validator import (
    REQUIRED_RENDERER_IDS,
    RendererRegistryValidationError,
    validate_renderer_registry,
)


RENDERER_REGISTRY_HEALTH_SCHEMA_VERSION = "renderer_registry_health@1"


def build_renderer_registry_health_payload() -> dict[str, object]:
    registry = _build_registry_status_payload()
    parity_result = verify_renderer_manifest_parity()
    parity_payload = parity_result.to_dict()
    ok = bool(registry.get("ok", False)) and parity_result.ok
    return {
        "ok": ok,
        "schema_version": RENDERER_REGISTRY_HEALTH_SCHEMA_VERSION,
        "registry": registry,
        "parity": parity_payload,
    }


def _build_registry_status_payload() -> dict[str, object]:
    required = sorted(REQUIRED_RENDERER_IDS)
    try:
        validation = validate_renderer_registry()
    except RendererRegistryValidationError as exc:
        return {
            "error_code": exc.error_code,
            "error_message": str(exc),
            "ok": False,
            "renderer_count": 0,
            "renderer_ids": [],
            "required_renderer_ids": required,
            "status": "invalid",
        }
    renderer_ids = sorted(validation.renderer_ids)
    return {
        "error_code": "",
        "error_message": "",
        "ok": True,
        "renderer_count": len(renderer_ids),
        "renderer_ids": list(renderer_ids),
        "required_renderer_ids": required,
        "status": "validated",
    }


__all__ = [
    "RENDERER_REGISTRY_HEALTH_SCHEMA_VERSION",
    "build_renderer_registry_health_payload",
]
