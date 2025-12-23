from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def resolve_app_path(app_path: str | None) -> Path:
    """
    Resolve an app.ai path.

    If no path is provided, the current working directory must contain a single .ai file.
    """
    if app_path:
        path = Path(app_path)
        if not path.exists():
            raise Namel3ssError(f"App file '{app_path}' not found")
        return path.resolve()
    root = Path.cwd()
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
