from __future__ import annotations

import os
import tempfile
from hashlib import sha256
from pathlib import Path


ENV_PERSIST_ROOT = "N3_PERSIST_ROOT"
FALLBACK_DIR = "namel3ss"
FALLBACK_NAMESPACE = "persist"


def resolve_project_root(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    if project_root:
        try:
            return Path(project_root).resolve()
        except Exception:
            return Path(project_root)
    if app_path:
        try:
            return Path(app_path).resolve().parent
        except Exception:
            return Path(app_path).parent
    return None


def resolve_persistence_root(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    env_root = _resolve_env_root()
    if env_root is not None:
        if _is_writable_dir(env_root, create=allow_create):
            return env_root
        fallback = _fallback_root(_seed_for(env_root))
        if allow_create:
            fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    candidate = resolve_project_root(project_root, app_path)
    if candidate is None:
        return None
    if _is_writable_dir(candidate, create=allow_create):
        return candidate
    fallback = _fallback_root(_seed_for(candidate))
    if allow_create:
        fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resolve_writable_path(path: Path | str) -> Path:
    target = Path(path)
    env_root = _resolve_env_root()
    if env_root is not None and not target.is_absolute():
        target = env_root / target
    if _is_writable_dir(target.parent, create=True):
        return target
    fallback = _fallback_root(_seed_for(target))
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / target.name


def _is_writable_dir(path: Path, *, create: bool) -> bool:
    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False
    else:
        if not path.exists():
            return False
    if not path.is_dir():
        return False
    try:
        if create:
            return os.access(path, os.W_OK | os.X_OK)
        return os.access(path, os.R_OK | os.X_OK)
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


def _resolve_env_root() -> Path | None:
    value = os.getenv(ENV_PERSIST_ROOT)
    if not value:
        return None
    try:
        path = Path(value).expanduser()
    except Exception:
        return Path(value)
    try:
        return path.resolve()
    except Exception:
        return path


__all__ = ["resolve_persistence_root", "resolve_project_root", "resolve_writable_path"]
