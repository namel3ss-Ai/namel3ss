from __future__ import annotations

from importlib import resources as importlib_resources
import json
from pathlib import Path
from typing import Any


def renderer_manifest_resource_path() -> Path:
    resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_manifest.json")
    try:
        return Path(resource)
    except TypeError:
        with importlib_resources.as_file(resource) as resolved:
            return Path(resolved)


def load_renderer_manifest_json(*, path: Path | None = None) -> dict[str, Any]:
    try:
        if path is not None:
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_manifest.json")
            payload = json.loads(resource.read_text(encoding="utf-8"))
    except OSError as exc:
        missing_path = path.as_posix() if isinstance(path, Path) else "studio/web/renderer_manifest.json"
        raise ValueError(f"renderer manifest is missing: {missing_path}") from exc
    except json.JSONDecodeError as exc:
        invalid_path = path.as_posix() if isinstance(path, Path) else "studio/web/renderer_manifest.json"
        raise ValueError(f"renderer manifest is not valid JSON: {invalid_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("renderer manifest root must be an object.")
    return payload


__all__ = ["load_renderer_manifest_json", "renderer_manifest_resource_path"]
