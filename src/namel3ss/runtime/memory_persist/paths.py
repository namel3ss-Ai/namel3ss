from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.persistence_paths import (
    resolve_persistence_root,
    resolve_project_root as _resolve_project_root,
)


MEMORY_DIR_NAME = ".namel3ss/memory"
SNAPSHOT_FILENAME = "memory_snapshot.json"
CHECKSUM_FILENAME = "memory_snapshot.sha256"


def resolve_project_root(*, project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return _resolve_project_root(project_root, app_path)


def memory_dir(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    for_write: bool = False,
    allow_create: bool | None = None,
) -> Path | None:
    if for_write:
        if allow_create is None:
            allow_create = True
        root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    else:
        root = resolve_project_root(project_root=project_root, app_path=app_path)
    if root is None:
        return None
    return root / ".namel3ss" / "memory"


def snapshot_path(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    for_write: bool = False,
    allow_create: bool | None = None,
) -> Path | None:
    root = memory_dir(
        project_root=project_root,
        app_path=app_path,
        for_write=for_write,
        allow_create=allow_create,
    )
    if root is None:
        return None
    return root / SNAPSHOT_FILENAME


def checksum_path(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    for_write: bool = False,
    allow_create: bool | None = None,
) -> Path | None:
    root = memory_dir(
        project_root=project_root,
        app_path=app_path,
        for_write=for_write,
        allow_create=allow_create,
    )
    if root is None:
        return None
    return root / CHECKSUM_FILENAME


def snapshot_paths(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    for_write: bool = False,
    allow_create: bool | None = None,
) -> tuple[Path | None, Path | None]:
    return (
        snapshot_path(
            project_root=project_root,
            app_path=app_path,
            for_write=for_write,
            allow_create=allow_create,
        ),
        checksum_path(
            project_root=project_root,
            app_path=app_path,
            for_write=for_write,
            allow_create=allow_create,
        ),
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
