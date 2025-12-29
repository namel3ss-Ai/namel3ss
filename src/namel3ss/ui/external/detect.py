from __future__ import annotations

from pathlib import Path


def resolve_external_ui_root(project_root: Path | str | None, app_path: Path | str | None) -> Path | None:
    root = _resolve_root(project_root, app_path)
    if root is None:
        return None
    ui_root = root / "ui"
    if ui_root.is_dir():
        return ui_root
    return None


def detect_external_ui(project_root: Path | str | None, app_path: Path | str | None) -> bool:
    return resolve_external_ui_root(project_root, app_path) is not None


def _resolve_root(project_root: Path | str | None, app_path: Path | str | None) -> Path | None:
    if project_root:
        return Path(project_root).resolve()
    if app_path:
        return Path(app_path).resolve().parent
    return None


__all__ = ["detect_external_ui", "resolve_external_ui_root"]
