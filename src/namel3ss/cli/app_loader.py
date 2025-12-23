from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path
from namel3ss.secrets import set_audit_root


def load_program(path_str: str, allow_legacy_type_aliases: bool = True) -> tuple[object, dict]:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError(
            f"App file not found: {path_str}\nWhy: namel3ss apps use the .ai extension.\nFix: run `n3 <app.ai> check` from your project folder."
        )
    apply_dotenv(load_dotenv_for_path(str(path)))
    project = load_project(path, allow_legacy_type_aliases=allow_legacy_type_aliases)
    set_audit_root(project.app_path.parent)
    return project.program, project.sources
