from __future__ import annotations

from dataclasses import dataclass
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Iterable

from namel3ss.runtime.ui.renderer.manifest_loader import load_renderer_manifest_json


RENDERER_MANIFEST_SCHEMA_VERSION = "renderer_registry@1"
RENDERER_REGISTRY_INVALID_ERROR_CODE = "N3E_RENDERER_REGISTRY_INVALID"
RENDERER_REQUIRED_MISSING_ERROR_CODE = "N3E_RENDERER_REQUIRED_MISSING"
REQUIRED_RENDERER_IDS: tuple[str, ...] = ("audit_viewer", "state_inspector")


@dataclass(frozen=True)
class RendererRegistryValidationResult:
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
        manifest = load_renderer_manifest_json(path=manifest_path)
    except ValueError as exc:
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message=str(exc),
        ) from exc

    schema_version = _normalized_text(manifest.get("schema_version"))
    if schema_version != RENDERER_MANIFEST_SCHEMA_VERSION:
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message=(
                f"renderer manifest schema_version must be "
                f"{RENDERER_MANIFEST_SCHEMA_VERSION}, got {schema_version or '<empty>'}."
            ),
        )

    renderers = manifest.get("renderers")
    if not isinstance(renderers, list):
        raise RendererRegistryValidationError(
            error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
            message="renderer manifest field 'renderers' must be a list.",
        )

    seen: set[str] = set()
    renderer_ids: list[str] = []
    for entry in renderers:
        if not isinstance(entry, dict):
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message="renderer manifest entries must be objects.",
            )
        renderer_id = _normalized_text(entry.get("renderer_id"))
        if renderer_id is None:
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message="renderer manifest field 'renderer_id' must be a non-empty string.",
            )
        if renderer_id in seen:
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"duplicate renderer id '{renderer_id}' in renderer manifest.",
            )
        seen.add(renderer_id)
        renderer_ids.append(renderer_id)

        entrypoint = _normalized_text(entry.get("entrypoint"))
        if entrypoint is None:
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"renderer '{renderer_id}' must define a non-empty entrypoint.",
            )
        if not _renderer_entrypoint_exists(entrypoint):
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"renderer entrypoint '{entrypoint}' is missing.",
            )

        exports = _normalized_exports(entry.get("exports"))
        if exports != sorted(exports):
            raise RendererRegistryValidationError(
                error_code=RENDERER_REGISTRY_INVALID_ERROR_CODE,
                message=f"renderer '{renderer_id}' exports must be sorted.",
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

    return RendererRegistryValidationResult(renderer_ids=tuple(renderer_ids))


def _renderer_entrypoint_exists(entrypoint: str) -> bool:
    try:
        candidate = importlib_resources.files("namel3ss").joinpath("studio", "web", entrypoint)
    except Exception:
        return False
    return candidate.is_file()


def _normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalized_exports(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    exports: list[str] = []
    for entry in value:
        text = _normalized_text(entry)
        if text is not None:
            exports.append(text)
    return exports


__all__ = [
    "RENDERER_MANIFEST_SCHEMA_VERSION",
    "RENDERER_REGISTRY_INVALID_ERROR_CODE",
    "RENDERER_REQUIRED_MISSING_ERROR_CODE",
    "REQUIRED_RENDERER_IDS",
    "RendererRegistryValidationError",
    "RendererRegistryValidationResult",
    "validate_renderer_registry",
]
