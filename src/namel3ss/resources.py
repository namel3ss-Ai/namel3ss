from __future__ import annotations

from contextlib import ExitStack
from importlib import resources as importlib_resources
from pathlib import Path
import sys

_RESOURCE_CONTEXTS = ExitStack()


def _resource_path(*parts: str) -> Path:
    resource = importlib_resources.files("namel3ss")
    for part in parts:
        resource = resource.joinpath(part)
    try:
        return Path(resource)
    except TypeError:
        return _RESOURCE_CONTEXTS.enter_context(importlib_resources.as_file(resource))


def package_root() -> Path:
    return _resource_path()


def templates_root() -> Path:
    return package_root() / "templates"


def examples_root() -> Path:
    return package_root() / "examples"


def demos_root() -> Path:
    return package_root() / "demos"


def studio_web_root() -> Path:
    return _resource_path("studio", "web")


def icons_root() -> Path:
    # Icons are installed alongside the package under a top-level resources/icons folder.
    candidates = [
        package_root().parent.parent / "resources" / "icons",
        package_root().parent / "resources" / "icons",
        Path(sys.prefix) / "resources" / "icons",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


__all__ = ["package_root", "templates_root", "examples_root", "demos_root", "studio_web_root", "icons_root"]
