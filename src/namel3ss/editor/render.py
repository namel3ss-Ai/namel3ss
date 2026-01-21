from __future__ import annotations

from pathlib import Path

from namel3ss.editor.workspace import normalize_path


def display_path(path: Path, root: Path) -> str:
    return normalize_path(path, root)


__all__ = ["display_path"]
