from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError


def read_source(path_str: str) -> tuple[str, str]:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError("Input file must have .ai extension")
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"File not found: {path}") from err
    return text, str(path)
