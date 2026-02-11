from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message

CANONICAL_ROOT_APP = "app.ai"


def discover_compile_app_path(
    target: str | None,
    *,
    project_root: str | None = None,
) -> Path:
    base = Path(project_root).resolve() if project_root else Path.cwd()
    if target:
        return _resolve_target(target, base=base)
    app_path = (base / CANONICAL_ROOT_APP).resolve()
    if app_path.exists() and app_path.is_file():
        return app_path
    raise Namel3ssError(_missing_root_message(base))


def _resolve_target(target: str, *, base: Path) -> Path:
    path = Path(target)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    if resolved.is_dir():
        root_app = (resolved / CANONICAL_ROOT_APP).resolve()
        if root_app.exists() and root_app.is_file():
            return root_app
        raise Namel3ssError(_missing_root_message(resolved))
    if not resolved.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Compile target not found: {target}.",
                why="The path does not exist.",
                fix="Pass a valid app.ai file path or project directory.",
                example="n3 compile app.ai --lang rust --flow demo",
            )
        )
    if resolved.suffix != ".ai":
        raise Namel3ssError(
            build_guidance_message(
                what="Compile target must be an .ai file or a project directory.",
                why="`n3 compile` accepts app.ai or a directory containing app.ai.",
                fix="Pass app.ai explicitly or the project folder.",
                example="n3 compile ./my_project --lang rust --flow demo",
            )
        )
    return resolved


def _missing_root_message(project_dir: Path) -> str:
    return build_guidance_message(
        what=f'Project root is missing "{CANONICAL_ROOT_APP}".',
        why="Directory compilation requires a canonical root file named app.ai.",
        fix=f'Add {CANONICAL_ROOT_APP} or pass an explicit .ai file path.',
        example=f"n3 compile {project_dir.as_posix()} --lang rust --flow demo",
    )


__all__ = ["CANONICAL_ROOT_APP", "discover_compile_app_path"]
