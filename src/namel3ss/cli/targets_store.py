from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.path_display import display_path_hint


BUILD_BASE_DIR = ".namel3ss/build"
LEGACY_BUILD_BASE_DIR = "build"
PROMOTION_STATE_FILE = ".namel3ss/promotion.json"
LATEST_FILENAME = "latest.json"
BUILD_META_FILENAME = "build.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_root(project_root: Path, target: str) -> Path:
    return project_root / BUILD_BASE_DIR / target


def legacy_build_root(project_root: Path, target: str) -> Path:
    return project_root / LEGACY_BUILD_BASE_DIR / target


def build_dir(project_root: Path, target: str, build_id: str) -> Path:
    return build_root(project_root, target) / build_id


def latest_pointer_path(project_root: Path, target: str) -> Path:
    return build_root(project_root, target) / LATEST_FILENAME


def legacy_build_dir(project_root: Path, target: str, build_id: str) -> Path:
    return legacy_build_root(project_root, target) / build_id


def legacy_latest_pointer_path(project_root: Path, target: str) -> Path:
    return legacy_build_root(project_root, target) / LATEST_FILENAME


def build_dir_candidates(project_root: Path, target: str, build_id: str) -> list[Path]:
    return [build_dir(project_root, target, build_id), legacy_build_dir(project_root, target, build_id)]


def latest_pointer_candidates(project_root: Path, target: str) -> list[Path]:
    return [latest_pointer_path(project_root, target), legacy_latest_pointer_path(project_root, target)]


def resolve_build_dir(project_root: Path, target: str, build_id: str) -> Path | None:
    for candidate in build_dir_candidates(project_root, target, build_id):
        if candidate.exists():
            return candidate
    return None


def promotion_state_path(project_root: Path) -> Path:
    return project_root / PROMOTION_STATE_FILE


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)


def read_json(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        safe_path = display_path_hint(path)
        raise Namel3ssError(
            build_guidance_message(
                what=f"File not found: {safe_path}",
                why="The expected build metadata file is missing.",
                fix="Re-run `n3 build` to regenerate artifacts.",
                example="n3 build --target service",
            )
        ) from err
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Invalid JSON in {path.name}.",
                why=str(err),
                fix="Regenerate the build artifacts.",
                example="n3 build --target local",
            )
        ) from err
    if not isinstance(data, dict):
        raise Namel3ssError(
            build_guidance_message(
                what=f"{path.name} does not contain an object.",
                why="Metadata files must be JSON objects.",
                fix="Re-run the build command to recreate the file.",
                example="n3 build --target edge",
            )
        )
    return data


__all__ = [
    "BUILD_BASE_DIR",
    "BUILD_META_FILENAME",
    "LEGACY_BUILD_BASE_DIR",
    "LATEST_FILENAME",
    "PROMOTION_STATE_FILE",
    "build_dir",
    "build_dir_candidates",
    "build_root",
    "ensure_dir",
    "latest_pointer_candidates",
    "latest_pointer_path",
    "legacy_build_dir",
    "legacy_build_root",
    "legacy_latest_pointer_path",
    "promotion_state_path",
    "read_json",
    "resolve_build_dir",
    "write_json",
]
