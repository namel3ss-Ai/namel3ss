from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets_store import (
    BUILD_META_FILENAME,
    latest_pointer_candidates,
    read_json,
    resolve_build_dir,
)
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.path_display import display_path_hint


def load_build_metadata(project_root: Path, target: str, build_id: str) -> Tuple[Path, Dict[str, Any]]:
    build_path = resolve_build_dir(project_root, target, build_id)
    if build_path is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Build '{build_id}' was not found.",
                why="The build folder is missing or was removed.",
                fix="Re-run `n3 pack` for the target.",
                example=f"n3 pack --target {target}",
            )
        )
    meta_path = build_path / BUILD_META_FILENAME
    meta = read_json(meta_path)
    return build_path, meta


def app_path_from_metadata(build_path: Path, metadata: Dict[str, Any]) -> Path:
    rel = metadata.get("app_relative_path")
    if not isinstance(rel, str) or not rel:
        raise Namel3ssError(
            build_guidance_message(
                what="Build metadata is missing the app path.",
                why="app_relative_path was not recorded.",
                fix="Re-run `n3 build` for this target.",
                example="n3 build --target service",
            )
        )
    path = build_path / "program" / rel
    if not path.exists():
        path_hint = display_path_hint(path, base=build_path)
        raise Namel3ssError(
            build_guidance_message(
                what=f"App snapshot not found at {path_hint}.",
                why="The build folder is incomplete.",
                fix="Re-run the build to regenerate program files.",
                example="n3 build --target local",
            )
        )
    return path


def read_latest_build_id(project_root: Path, target: str) -> str | None:
    for pointer in latest_pointer_candidates(project_root, target):
        if not pointer.exists():
            continue
        data = read_json(pointer)
        build_id = data.get("build_id") if isinstance(data, dict) else None
        if build_id:
            return str(build_id)
    return None


def resolve_build_id(project_root: Path, target: str, requested: str | None) -> str | None:
    chosen = requested
    if target != "local" and chosen is None:
        state = load_state(project_root)
        active = state.get("active") or {}
        if active.get("target") == target and active.get("build_id"):
            chosen = active.get("build_id")
        elif target in {"service", "edge"}:
            latest = read_latest_build_id(project_root, target)
            if latest:
                chosen = latest
    return chosen


__all__ = ["app_path_from_metadata", "load_build_metadata", "read_latest_build_id", "resolve_build_id"]
