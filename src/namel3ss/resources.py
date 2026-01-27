from __future__ import annotations

from pathlib import Path
import sys


def package_root() -> Path:
    return Path(__file__).resolve().parent


def templates_root() -> Path:
    return package_root() / "templates"


def examples_root() -> Path:
    return package_root() / "examples"


def demos_root() -> Path:
    return package_root() / "demos"


def studio_web_root() -> Path:
    return package_root() / "studio" / "web"


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
