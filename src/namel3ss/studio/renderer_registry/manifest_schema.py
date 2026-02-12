from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


RENDERER_MANIFEST_SCHEMA_VERSION = "renderer_registry@1"


@dataclass(frozen=True)
class RendererManifestEntry:
    renderer_id: str
    entrypoint: str
    entrypoint_hash: str
    version: str
    integrity_hash: str
    exports: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "entrypoint": self.entrypoint,
            "entrypoint_hash": self.entrypoint_hash,
            "exports": list(self.exports),
            "integrity_hash": self.integrity_hash,
            "renderer_id": self.renderer_id,
            "version": self.version,
        }


@dataclass(frozen=True)
class RendererManifest:
    schema_version: str
    renderers: tuple[RendererManifestEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "renderers": [entry.to_dict() for entry in self.renderers],
            "schema_version": self.schema_version,
        }


def build_renderer_entry(value: Mapping[str, object]) -> RendererManifestEntry:
    renderer_id = _required_text(value, "renderer_id")
    entrypoint = _required_text(value, "entrypoint")
    entrypoint_hash = _required_text(value, "entrypoint_hash")
    version = _required_text(value, "version")
    integrity_hash = _required_text(value, "integrity_hash")
    exports = _string_list(value.get("exports"))
    return RendererManifestEntry(
        renderer_id=renderer_id,
        entrypoint=entrypoint,
        entrypoint_hash=entrypoint_hash,
        version=version,
        integrity_hash=integrity_hash,
        exports=tuple(exports),
    )


def build_renderer_manifest(value: Mapping[str, object]) -> RendererManifest:
    schema_version = _required_text(value, "schema_version")
    renderers_value = value.get("renderers")
    if not isinstance(renderers_value, Sequence) or isinstance(renderers_value, (str, bytes)):
        raise ValueError("renderer manifest field 'renderers' must be a list.")
    entries: list[RendererManifestEntry] = []
    for item in renderers_value:
        if not isinstance(item, Mapping):
            raise ValueError("renderer manifest entries must be objects.")
        entries.append(build_renderer_entry(item))
    return RendererManifest(schema_version=schema_version, renderers=tuple(entries))


def _required_text(value: Mapping[str, object], key: str) -> str:
    raw = value.get(key)
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        raise ValueError(f"renderer manifest field '{key}' must be a non-empty string.")
    return text


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            result.append(text)
    return result


__all__ = [
    "RENDERER_MANIFEST_SCHEMA_VERSION",
    "RendererManifest",
    "RendererManifestEntry",
    "build_renderer_entry",
    "build_renderer_manifest",
]
