from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.persistence_paths import resolve_persistence_root
from namel3ss.utils.slugify import slugify_tool_name


def foreign_workspace_dir(
    tool_name: str,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    base = root / ".namel3ss" / "foreign"
    if allow_create:
        base.mkdir(parents=True, exist_ok=True)
    return base / slugify_tool_name(tool_name)


__all__ = ["foreign_workspace_dir"]
