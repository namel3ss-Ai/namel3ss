from __future__ import annotations

from functools import lru_cache

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.studio.renderer_registry.registry_validator import (
    RENDERER_REGISTRY_INVALID_ERROR_CODE,
    RENDERER_REQUIRED_MISSING_ERROR_CODE,
    RendererRegistryValidationError,
    validate_renderer_registry,
)


@lru_cache(maxsize=1)
def _cached_validate_renderer_registry_startup() -> tuple[str, ...]:
    result = validate_renderer_registry()
    return result.renderer_ids


def validate_renderer_registry_startup() -> tuple[str, ...]:
    try:
        return _cached_validate_renderer_registry_startup()
    except RendererRegistryValidationError as exc:
        if exc.error_code == RENDERER_REQUIRED_MISSING_ERROR_CODE:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{RENDERER_REQUIRED_MISSING_ERROR_CODE}: required Studio renderer is missing.",
                    why=str(exc),
                    fix="Regenerate renderer assets and restart Studio/runtime.",
                    example="python tools/build_renderer_manifest.py",
                ),
                details={"error_code": RENDERER_REQUIRED_MISSING_ERROR_CODE, "category": "engine"},
            ) from exc
        raise Namel3ssError(
            build_guidance_message(
                what=f"{RENDERER_REGISTRY_INVALID_ERROR_CODE}: renderer registry manifest is invalid.",
                why=str(exc),
                fix="Regenerate renderer manifest and registry loader.",
                example="python tools/build_renderer_manifest.py",
            ),
            details={"error_code": RENDERER_REGISTRY_INVALID_ERROR_CODE, "category": "engine"},
        ) from exc


def reset_renderer_registry_startup_cache() -> None:
    _cached_validate_renderer_registry_startup.cache_clear()


__all__ = ["reset_renderer_registry_startup_cache", "validate_renderer_registry_startup"]
