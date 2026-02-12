from __future__ import annotations

from dataclasses import dataclass
from importlib import resources as importlib_resources

from namel3ss.studio.renderer_registry.registry_validator import (
    RendererRegistryValidationResult,
    validate_renderer_registry,
)


@dataclass(frozen=True)
class LoadedRendererAsset:
    renderer_id: str
    entrypoint: str
    exports: tuple[str, ...]
    source: str


def load_renderer_assets() -> tuple[LoadedRendererAsset, ...]:
    validation = validate_renderer_registry()
    return _load_assets(validation)


def _load_assets(validation: RendererRegistryValidationResult) -> tuple[LoadedRendererAsset, ...]:
    assets: list[LoadedRendererAsset] = []
    for entry in validation.manifest.renderers:
        source = (
            importlib_resources.files("namel3ss")
            .joinpath("studio", "web", entry.entrypoint)
            .read_text(encoding="utf-8")
        )
        assets.append(
            LoadedRendererAsset(
                renderer_id=entry.renderer_id,
                entrypoint=entry.entrypoint,
                exports=entry.exports,
                source=source,
            )
        )
    return tuple(assets)


__all__ = ["LoadedRendererAsset", "load_renderer_assets"]
