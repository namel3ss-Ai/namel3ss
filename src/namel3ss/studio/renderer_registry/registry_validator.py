from __future__ import annotations

from dataclasses import dataclass
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Iterable

from namel3ss.studio.renderer_registry.manifest_loader import load_renderer_manifest
from namel3ss.studio.renderer_registry.manifest_schema import (
    RENDERER_MANIFEST_SCHEMA_VERSION,
    RendererManifest,
)


RENDERER_REGISTRY_INVALID_ERROR_CODE = "N3E_RENDERER_REGISTRY_INVALID"
RENDERER_REQUIRED_MISSING_ERROR_CODE = "N3E_RENDERER_REQUIRED_MISSING"
REQUIRED_RENDERER_IDS: tuple[str, ...] = ("audit_viewer", "state_inspector")


@dataclass(frozen=True)
class RendererRegistryValidationResult:
    manifest: RendererManifest
    renderer_ids: tuple[str, ...]


class RendererRegistryValidationError(ValueError):
    def __init__(self, *, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def validate_renderer_registry(
    *,
    required_renderer_ids: Iterable[str] = REQUIRED_RENDERER_IDS,
    manifest_path: Path | None = None,
) -> RendererRegistryValidationResult:
    try:
        manifest = load_renderer_manifest(path=manifest_path)
    except ValueError as exc:
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message=str(exc),
        ) from exc

    if manifest.schema_version != RENDERER_MANIFEST_SCHEMA_VERSION:
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message=(
                f"renderer manifest schema_version must be "
                f"{RENDERER_MANIFEST_SCHEMA_VERSION}, got {manifest.schema_version}."
            ),
        )

    seen: set[str] = set()
    renderer_ids: list[str] = []
    for entry in manifest.renderers:
        if entry.renderer_id in seen:
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"duplicate renderer id '{entry.renderer_id}' in renderer manifest.",
            )
        seen.add(entry.renderer_id)
        renderer_ids.append(entry.renderer_id)
        if list(entry.exports) != sorted(entry.exports):
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"renderer '{entry.renderer_id}' exports must be sorted.",
            )
        if not _renderer_entrypoint_exists(entry.entrypoint):
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"renderer entrypoint '{entry.entrypoint}' is missing.",
            )

    if renderer_ids != sorted(renderer_ids):
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message="renderer manifest entries must be sorted by renderer_id.",
        )

    required = sorted({item.strip() for item in required_renderer_ids if isinstance(item, str) and item.strip()})
    missing = [renderer_id for renderer_id in required if renderer_id not in seen]
    if missing:
        raise RendererRegistryValidationError(
            error_code=RENDERER_REQUIRED_MISSING_ERROR_CODE,
            message=f"required renderer(s) missing: {', '.join(missing)}.",
        )

    return RendererRegistryValidationResult(manifest=manifest, renderer_ids=tuple(renderer_ids))


def _renderer_entrypoint_exists(entrypoint: str) -> bool:
    try:
        candidate = importlib_resources.files("namel3ss").joinpath("studio", "web", entrypoint)
    except Exception:
        return False
    return candidate.is_file()


__all__ = [
    "RENDERER_REGISTRY_INVALID_ERROR_CODE",
    "RENDERER_REQUIRED_MISSING_ERROR_CODE",
    "REQUIRED_RENDERER_IDS",
    "RendererRegistryValidationError",
    "RendererRegistryValidationResult",
    "validate_renderer_registry",
]
