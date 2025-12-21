from __future__ import annotations

from importlib import metadata
from pathlib import Path


def get_version() -> str:
    try:
        return metadata.version("namel3ss")
    except metadata.PackageNotFoundError:
        version_file = Path(__file__).resolve().parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
        return "0.0.0"
