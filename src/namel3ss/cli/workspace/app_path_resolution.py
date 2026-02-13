from __future__ import annotations

import os
from pathlib import Path

from namel3ss.cli.workspace.resolution_contract import WorkspaceResolutionContract


DEFAULT_SCAN_DEPTH = 2
_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".namel3ss",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


def build_workspace_app_resolution(
    *,
    search_root: Path,
    default_name: str = "app.ai",
    max_depth: int = DEFAULT_SCAN_DEPTH,
) -> WorkspaceResolutionContract:
    root = Path(search_root).resolve()
    candidates = discover_workspace_app_paths(
        search_root=root,
        default_name=default_name,
        max_depth=max_depth,
    )
    root_default = (root / default_name).resolve()
    selected: Path | None = None
    mode = "workspace_none"
    if root_default in candidates:
        selected = root_default
        mode = "workspace_root_default"
    elif candidates:
        selected = candidates[0]
        mode = "workspace_scan"
    alternatives = tuple(path for path in candidates if path != selected)
    return WorkspaceResolutionContract(
        search_root=root,
        selected_app_path=selected,
        candidate_app_paths=candidates,
        alternative_app_paths=alternatives,
        resolution_mode=mode,
        warning_required=selected is not None and len(candidates) > 1,
    )


def discover_workspace_app_paths(
    *,
    search_root: Path,
    default_name: str = "app.ai",
    max_depth: int = DEFAULT_SCAN_DEPTH,
) -> tuple[Path, ...]:
    root = Path(search_root).resolve()
    if not root.exists() or not root.is_dir():
        return ()
    depth_limit = max(0, int(max_depth))
    discovered: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root, topdown=True):
        current_path = Path(current_root)
        relative_depth = len(current_path.relative_to(root).parts)
        dir_names[:] = _normalized_child_dirs(
            root=root,
            current_path=current_path,
            child_names=dir_names,
            max_depth=depth_limit,
        )
        if relative_depth > depth_limit:
            continue
        if default_name in file_names:
            discovered.append((current_path / default_name).resolve())
    unique = sorted(
        set(discovered),
        key=lambda path: (_relative_depth(root, path), path.as_posix()),
    )
    return tuple(unique)


def _normalized_child_dirs(
    *,
    root: Path,
    current_path: Path,
    child_names: list[str],
    max_depth: int,
) -> list[str]:
    if len(current_path.relative_to(root).parts) >= max_depth:
        return []
    filtered: list[str] = []
    for name in sorted(child_names):
        if not name:
            continue
        if name in _SKIP_DIR_NAMES:
            continue
        if name.startswith("."):
            continue
        filtered.append(name)
    return filtered


def _relative_depth(root: Path, path: Path) -> int:
    return len(path.resolve().relative_to(root.resolve()).parts)


__all__ = [
    "DEFAULT_SCAN_DEPTH",
    "build_workspace_app_resolution",
    "discover_workspace_app_paths",
]
