from __future__ import annotations

import os
import tempfile
from hashlib import sha256
from pathlib import Path


FALLBACK_DIR = "namel3ss"
FALLBACK_NAMESPACE = "persist"


def resolve_project_root(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    if project_root:
        return Path(project_root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None


def resolve_persistence_root(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    candidate = resolve_project_root(project_root, app_path)
    if candidate is None:
        return None
    if _is_writable_dir(candidate):
        return candidate
    fallback = _fallback_root(_seed_for(candidate))
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resolve_writable_path(path: Path | str) -> Path:
    target = Path(path)
    if _is_writable_dir(target.parent):
        return target
    fallback = _fallback_root(_seed_for(target))
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / target.name


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    if not path.is_dir():
        return False
    try:
        return os.access(path, os.W_OK | os.X_OK)
    except Exception:
        return False


def _seed_for(path: Path) -> str:
    try:
        return path.resolve().as_posix()
    except Exception:
        return path.as_posix()


def _fallback_root(seed: str) -> Path:
    digest = sha256(seed.encode("utf-8")).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / FALLBACK_DIR / FALLBACK_NAMESPACE / digest


__all__ = ["resolve_persistence_root", "resolve_project_root", "resolve_writable_path"]
