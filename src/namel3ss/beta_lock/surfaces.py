from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SURFACES_PATH = Path("resources/beta_surfaces.json")


@dataclass(frozen=True)
class SurfaceSpec:
    surface_id: str
    version: str
    artifacts: tuple[str, ...]


def load_surfaces(path: Path | None = None) -> tuple[SurfaceSpec, ...]:
    source = path or SURFACES_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("beta surfaces payload must be an object")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise ValueError("beta surfaces payload missing schema_version")
    raw_surfaces = payload.get("surfaces")
    if not isinstance(raw_surfaces, list):
        raise ValueError("beta surfaces payload missing surfaces list")
    surfaces: list[SurfaceSpec] = []
    seen: set[str] = set()
    for entry in raw_surfaces:
        if not isinstance(entry, dict):
            raise ValueError("beta surfaces entry must be an object")
        surface_id = entry.get("id")
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError("beta surfaces entry missing id")
        if surface_id in seen:
            raise ValueError(f"beta surfaces duplicate id '{surface_id}'")
        seen.add(surface_id)
        version = entry.get("version")
        if not isinstance(version, str) or not version:
            raise ValueError(f"beta surfaces entry '{surface_id}' missing version")
        artifacts = entry.get("artifacts")
        if not isinstance(artifacts, list) or not all(isinstance(item, str) for item in artifacts):
            raise ValueError(f"beta surfaces entry '{surface_id}' missing artifacts list")
        surfaces.append(SurfaceSpec(surface_id=surface_id, version=version, artifacts=tuple(artifacts)))
    return tuple(surfaces)


__all__ = ["SurfaceSpec", "SURFACES_PATH", "load_surfaces"]
