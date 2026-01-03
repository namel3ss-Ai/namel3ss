from __future__ import annotations

from importlib import metadata
from pathlib import Path


def get_version() -> str:
    try:
        return metadata.version("namel3ss")
    except metadata.PackageNotFoundError:
        version_file = _find_version_file()
        if version_file is not None:
            return version_file.read_text(encoding="utf-8").strip()
        return "0.0.0"


def _find_version_file() -> Path | None:
    base = Path(__file__).resolve()
    candidates = [
        base.parent / "VERSION",
        base.parent.parent / "VERSION",
        base.parent.parent.parent / "VERSION",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
