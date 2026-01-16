from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def templates_root() -> Path:
    return package_root() / "templates"


def examples_root() -> Path:
    return package_root() / "examples"


def studio_web_root() -> Path:
    return package_root() / "studio" / "web"


def icons_root() -> Path:
    # Icons are installed alongside the package under a top-level resources/icons folder.
    root = package_root().parent.parent / "resources" / "icons"
    if not root.exists():
        alt = package_root().parent / "resources" / "icons"
        if alt.exists():
            return alt
    return root


__all__ = ["package_root", "templates_root", "examples_root", "studio_web_root", "icons_root"]
