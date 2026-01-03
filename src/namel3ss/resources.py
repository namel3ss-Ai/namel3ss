from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def templates_root() -> Path:
    return package_root() / "templates"


def studio_web_root() -> Path:
    return package_root() / "studio" / "web"


__all__ = ["package_root", "templates_root", "studio_web_root"]
