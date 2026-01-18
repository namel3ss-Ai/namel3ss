from __future__ import annotations

from pathlib import Path


def display_path(value: str | Path) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    return str(value).replace("\\", "/")

def display_path_hint(value: str | Path, *, base: Path | None = None) -> str:
    if isinstance(value, Path):
        path = value
    else:
        try:
            path = Path(str(value))
        except Exception:
            return str(value).replace("\\", "/")
    base_path = base if base is not None else Path.cwd()
    if not path.is_absolute():
        return path.as_posix()
    try:
        relative = path.resolve().relative_to(base_path.resolve())
        return relative.as_posix()
    except Exception:
        return path.name or path.as_posix()


__all__ = ["display_path", "display_path_hint"]
