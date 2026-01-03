from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def resolve_app_path(
    app_path: str | None,
    *,
    project_root: str | None = None,
    search_parents: bool = True,
) -> Path:
    """
    Resolve an app.ai path.

    If no path is provided, search for app.ai from the current directory (and parents when enabled).
    """
    if app_path:
        path = Path(app_path)
        if project_root and not path.is_absolute():
            path = Path(project_root) / path
        if not path.exists():
            raise Namel3ssError(
                build_guidance_message(
                    what=f"App file not found: {app_path}.",
                    why="The path does not exist.",
                    fix="Check the path or run from the project folder.",
                    example="n3 app.ai check",
                )
            )
        return path.resolve()
    if project_root:
        return _resolve_app_in_dir(Path(project_root).resolve())
    root = Path.cwd()
    search_roots = [root]
    if search_parents:
        search_roots.extend(root.parents)
    for candidate in search_roots:
        app_file = candidate / "app.ai"
        if app_file.exists():
            ai_files = sorted(candidate.glob("*.ai"))
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
    return _raise_missing_app_error(root)


def _resolve_app_in_dir(root: Path) -> Path:
    ai_files = sorted(root.glob("*.ai"))
    app_file = root / "app.ai"
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
    return _raise_missing_app_error(root)


def _raise_missing_app_error(root: Path) -> Path:
    ai_files = sorted(root.glob("*.ai"))
    if not ai_files:
        raise Namel3ssError(
            build_guidance_message(
                what="No .ai app file found in this directory.",
                why="`n3` commands run from a project folder containing app.ai.",
                fix="Run inside the folder that contains app.ai or pass the file path explicitly.",
                example="n3 app.ai data",
            )
        )
    sample = ", ".join(path.name for path in ai_files)
    raise Namel3ssError(
        build_guidance_message(
            what="app.ai was not found in this directory.",
            why=f"Found other .ai files: {sample}.",
            fix="Pass the app file path explicitly.",
            example=f"n3 {ai_files[0].name} data",
        )
    )


__all__ = ["resolve_app_path"]
