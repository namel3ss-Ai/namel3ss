from __future__ import annotations

from pathlib import Path


def display_path(value: str | Path) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    return str(value).replace("\\", "/")


__all__ = ["display_path"]
