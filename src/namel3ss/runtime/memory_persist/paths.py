from __future__ import annotations

from pathlib import Path


MEMORY_DIR_NAME = ".namel3ss/memory"
SNAPSHOT_FILENAME = "memory_snapshot.json"
CHECKSUM_FILENAME = "memory_snapshot.sha256"


def resolve_project_root(*, project_root: str | None, app_path: str | None) -> Path | None:
    if project_root:
        return Path(project_root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None


def memory_dir(*, project_root: str | None, app_path: str | None) -> Path | None:
    root = resolve_project_root(project_root=project_root, app_path=app_path)
    if root is None:
        return None
    return root / ".namel3ss" / "memory"


def snapshot_path(*, project_root: str | None, app_path: str | None) -> Path | None:
    root = memory_dir(project_root=project_root, app_path=app_path)
    if root is None:
        return None
    return root / SNAPSHOT_FILENAME


def checksum_path(*, project_root: str | None, app_path: str | None) -> Path | None:
    root = memory_dir(project_root=project_root, app_path=app_path)
    if root is None:
        return None
    return root / CHECKSUM_FILENAME


def snapshot_paths(*, project_root: str | None, app_path: str | None) -> tuple[Path | None, Path | None]:
    return (
        snapshot_path(project_root=project_root, app_path=app_path),
        checksum_path(project_root=project_root, app_path=app_path),
    )


__all__ = [
    "CHECKSUM_FILENAME",
    "MEMORY_DIR_NAME",
    "SNAPSHOT_FILENAME",
    "checksum_path",
    "memory_dir",
    "resolve_project_root",
    "snapshot_path",
    "snapshot_paths",
]
