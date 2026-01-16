from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def resolve_app_path(
    app_path: str | None,
    *,
    project_root: str | None = None,
    search_parents: bool = True,
    default_name: str = "app.ai",
    missing_message: str | None = None,
) -> Path:
    """
    Resolve an app.ai path.

    If no path is provided, search for default_name from the current directory (and parents when enabled).
    """
    base_root = Path(project_root).resolve() if project_root else Path.cwd()
    if app_path:
        return _resolve_explicit_path(app_path, base_root)
    if search_parents:
        resolved = _resolve_with_parent_search(base_root, default_name)
        if resolved:
            return resolved
    candidate = (base_root / default_name).resolve()
    if candidate.exists():
        return candidate
    raise _raise_missing_app_error(base_root, default_name, missing_message)


def _resolve_explicit_path(app_path: str, base_root: Path) -> Path:
    path = Path(app_path)
    if not path.is_absolute():
        path = base_root / path
    resolved = path.resolve()
    if not resolved.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"App file not found: {app_path}.",
                why="The path does not exist.",
                fix="Check the path or run from the project folder.",
                example="n3 app.ai check",
            )
        )
    if resolved.is_dir() or resolved.suffix != ".ai":
        raise Namel3ssError(
            build_guidance_message(
                what="namel3ss apps use the .ai extension.",
                why="Only .ai files can be executed.",
                fix="Pass a .ai file path.",
                example="n3 run app.ai",
            )
        )
    return resolved


def _resolve_with_parent_search(root: Path, default_name: str) -> Path | None:
    search_roots = [root, *list(root.parents)]
    for candidate_root in search_roots:
        resolved = _resolve_app_in_dir(candidate_root, default_name)
        if resolved:
            return resolved
    return None


def _resolve_app_in_dir(root: Path, default_name: str) -> Path | None:
    ai_files = sorted(root.glob("*.ai"))
    app_file = root / default_name
    if app_file.exists():
        if len(ai_files) > 1:
            sample = ", ".join(path.name for path in ai_files)
            raise Namel3ssError(
                build_guidance_message(
                    what="Multiple .ai files found in this directory.",
                    why=f"Found: {sample}.",
                    fix="Pass the app file path explicitly.",
                    example="n3 app.ai data",
                )
            )
        return app_file.resolve()
    return None


def _raise_missing_app_error(root: Path, default_name: str, missing_message: str | None) -> Path:
    if missing_message:
        raise Namel3ssError(missing_message)
    ai_files = sorted(root.glob("*.ai"))
    if not ai_files:
        raise Namel3ssError(
            build_guidance_message(
                what=f"No {default_name} file found in this directory.",
                why="`n3` commands run from a project folder containing the app file.",
                fix="Run inside the folder that contains your app or pass the file path explicitly.",
                example=f"n3 {default_name} data",
            )
        )
    sample = ", ".join(path.name for path in ai_files)
    raise Namel3ssError(
        build_guidance_message(
            what=f"{default_name} was not found in this directory.",
            why=f"Found other .ai files: {sample}.",
            fix="Pass the app file path explicitly.",
            example=f"n3 {ai_files[0].name} data",
        )
    )


def default_missing_app_message(command: str, *, default_name: str = "app.ai") -> str:
    return f"No {default_name} found. Run `n3 {command} <file.ai>` or create {default_name}."


__all__ = ["resolve_app_path", "default_missing_app_message"]
