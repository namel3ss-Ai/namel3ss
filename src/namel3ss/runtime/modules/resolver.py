from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def resolve_module_path(project_root: Path, raw_path: str) -> Path:
    if not raw_path or not raw_path.strip():
        raise Namel3ssError(
            build_guidance_message(
                what="Module path is missing.",
                why="Module paths must point to a .ai file inside the project.",
                fix="Provide a module path string after use module.",
                example='use module "modules/common.ai" as common',
            )
        )
    normalized = raw_path.replace("\\", "/").strip()
    path = Path(normalized)
    if path.is_absolute() or path.drive:
        raise Namel3ssError(
            build_guidance_message(
                what="Module path must be relative.",
                why="Modules are loaded from the project root only.",
                fix="Use a path like modules/common.ai.",
                example='use module "modules/common.ai" as common',
            )
        )
    root_resolved = project_root.resolve()
    target = (root_resolved / path).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Module path escapes the project root.",
                why="Paths cannot traverse above the project folder.",
                fix="Use a path within the project root.",
                example='use module "modules/common.ai" as common',
            )
        ) from err
    if target.suffix != ".ai":
        raise Namel3ssError(
            build_guidance_message(
                what="Module path must end with .ai.",
                why="Modules are plain ai files.",
                fix="Use a .ai file path.",
                example='use module "modules/common.ai" as common',
            )
        )
    return target


def module_id_for_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


__all__ = ["module_id_for_path", "resolve_module_path"]
