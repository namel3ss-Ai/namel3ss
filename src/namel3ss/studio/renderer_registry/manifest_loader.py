from __future__ import annotations

import json
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

from namel3ss.studio.renderer_registry.manifest_schema import RendererManifest, build_renderer_manifest


def renderer_manifest_resource_path() -> Path:
    resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_manifest.json")
    try:
        return Path(resource)
    except TypeError:
        with importlib_resources.as_file(resource) as resolved:
            return Path(resolved)


def load_renderer_manifest(*, path: Path | None = None) -> RendererManifest:
    if path is None:
        resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_manifest.json")
        try:
            payload = json.loads(resource.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValueError("renderer manifest is missing: studio/web/renderer_manifest.json") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("renderer manifest is not valid JSON: studio/web/renderer_manifest.json") from exc
    else:
        resolved = path
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValueError(f"renderer manifest is missing: {resolved.as_posix()}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"renderer manifest is not valid JSON: {resolved.as_posix()}") from exc
    if not isinstance(payload, dict):
        raise ValueError("renderer manifest root must be an object.")
    return build_renderer_manifest(payload)


def load_renderer_manifest_json(*, path: Path | None = None) -> dict[str, Any]:
    manifest = load_renderer_manifest(path=path)
    return manifest.to_dict()


__all__ = ["load_renderer_manifest", "load_renderer_manifest_json", "renderer_manifest_resource_path"]
