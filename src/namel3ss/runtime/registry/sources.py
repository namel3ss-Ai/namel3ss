from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig, RegistrySourceConfig
from namel3ss.runtime.registry.layout import registry_index_path


@dataclass(frozen=True)
class RegistrySource:
    id: str
    kind: str
    path: Path | None = None
    url: str | None = None


def resolve_registry_sources(app_root: Path, config: AppConfig) -> tuple[list[RegistrySource], list[str]]:
    sources: list[RegistrySource] = []
    default_ids = list(config.registries.default) if config.registries.default else []
    for entry in config.registries.sources:
        sources.append(_source_from_config(entry, app_root))
    if not sources:
        sources.append(_default_local(app_root))
    if not any(source.kind == "local_index" for source in sources):
        sources.append(_default_local(app_root))
    if not default_ids:
        default_ids = [source.id for source in sources if source.kind == "local_index"] or [sources[0].id]
    return sources, default_ids


def _source_from_config(entry: RegistrySourceConfig, app_root: Path) -> RegistrySource:
    path = Path(entry.path).expanduser() if entry.path else None
    if path and not path.is_absolute():
        path = app_root / path
    return RegistrySource(id=entry.id, kind=entry.kind, path=path, url=entry.url)


def _default_local(app_root: Path) -> RegistrySource:
    return RegistrySource(id="local", kind="local_index", path=registry_index_path(app_root))


__all__ = ["RegistrySource", "resolve_registry_sources"]
