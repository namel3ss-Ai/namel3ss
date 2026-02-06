from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.persistence_paths import resolve_project_root


GOVERNANCE_DIR = ".namel3ss"


def project_root_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return resolve_project_root(project_root, app_path)


def governance_dir(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = project_root_path(project_root, app_path)
    if root is None:
        return None
    return root / GOVERNANCE_DIR


def governance_file(project_root: str | Path | None, app_path: str | Path | None, filename: str) -> Path | None:
    base = governance_dir(project_root, app_path)
    if base is None:
        return None
    return base / filename


def root_file(project_root: str | Path | None, app_path: str | Path | None, filename: str) -> Path | None:
    root = project_root_path(project_root, app_path)
    if root is None:
        return None
    return root / filename


def existing_config_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    primary_name: str,
    fallback_name: str | None = None,
) -> Path | None:
    root_primary = root_file(project_root, app_path, primary_name)
    if root_primary is not None and root_primary.exists():
        return root_primary
    gov_primary = governance_file(project_root, app_path, primary_name)
    if gov_primary is not None and gov_primary.exists():
        return gov_primary
    if fallback_name:
        root_fallback = root_file(project_root, app_path, fallback_name)
        if root_fallback is not None and root_fallback.exists():
            return root_fallback
        gov_fallback = governance_file(project_root, app_path, fallback_name)
        if gov_fallback is not None and gov_fallback.exists():
            return gov_fallback
    return root_primary or gov_primary


__all__ = [
    "GOVERNANCE_DIR",
    "existing_config_path",
    "governance_dir",
    "governance_file",
    "project_root_path",
    "root_file",
]
