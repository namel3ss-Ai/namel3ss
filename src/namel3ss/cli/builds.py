from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from namel3ss.cli.targets_store import BUILD_META_FILENAME, build_dir, latest_pointer_path, read_json
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def load_build_metadata(project_root: Path, target: str, build_id: str) -> Tuple[Path, Dict[str, Any]]:
    build_path = build_dir(project_root, target, build_id)
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
        raise Namel3ssError(
            build_guidance_message(
                what=f"App snapshot not found at {path.as_posix()}.",
                why="The build folder is incomplete.",
                fix="Re-run the build to regenerate program files.",
                example="n3 build --target local",
            )
        )
    return path


def read_latest_build_id(project_root: Path, target: str) -> str | None:
    pointer = latest_pointer_path(project_root, target)
    if not pointer.exists():
        return None
    data = read_json(pointer)
    build_id = data.get("build_id") if isinstance(data, dict) else None
    if not build_id:
        return None
    return str(build_id)


__all__ = ["app_path_from_metadata", "load_build_metadata", "read_latest_build_id"]
