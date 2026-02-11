from __future__ import annotations

from pathlib import Path

from namel3ss.cli.project_discovery import discover_compile_app_path


def resolve_compile_entry_path(
    target: str | None,
    *,
    project_root: str | None = None,
) -> Path:
    return discover_compile_app_path(target, project_root=project_root)


__all__ = ["resolve_compile_entry_path"]
