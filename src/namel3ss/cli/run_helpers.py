from __future__ import annotations

import re
from pathlib import Path

from namel3ss.cli.builds import app_path_from_metadata, load_build_metadata, resolve_build_id


def resolve_run_path(target: str, project_root: Path, app_path: Path, build_id: str | None) -> tuple[Path, str | None]:
    chosen_build = resolve_build_id(project_root, target, build_id)
    if chosen_build:
        build_path, meta = load_build_metadata(project_root, target, chosen_build)
        return app_path_from_metadata(build_path, meta), chosen_build
    return app_path, None


def detect_demo_provider(app_path: Path) -> str | None:
    try:
        contents = app_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'provider\\s+is\\s+"([^"]+)"', contents)
    if not match:
        return None
    return match.group(1).strip().lower()


__all__ = ["detect_demo_provider", "resolve_run_path"]
