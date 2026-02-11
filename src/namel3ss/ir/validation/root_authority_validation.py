from __future__ import annotations

from collections.abc import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.program_loader import IncludeProgramEntry


def validate_root_authority(include_entries: Iterable[IncludeProgramEntry]) -> None:
    for entry in include_entries:
        program = entry.program
        if _declares_root_only_sections(program):
            raise Namel3ssError(
                f'Compile error: only the root file may define \'ui\' and \'pages\'. Found in "{entry.path_norm}"'
            )


def _declares_root_only_sections(program) -> bool:
    if list(getattr(program, "pages", []) or []):
        return True
    if getattr(program, "app_theme_line", None) is not None:
        return True
    if getattr(program, "theme_definition", None) is not None:
        return True
    if getattr(program, "ui_line", None) is not None:
        return True
    if getattr(program, "ui_state", None) is not None:
        return True
    if getattr(program, "app_permissions", None) is not None:
        return True
    return False


__all__ = ["validate_root_authority"]
