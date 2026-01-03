from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.format.formatter import format_source


def run_format(path_str: str, check_only: bool) -> int:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError(
            build_guidance_message(
                what="Input file must have .ai extension.",
                why="namel3ss apps are stored as .ai files.",
                fix="Pass a .ai file path to n3 fmt.",
                example="n3 app.ai fmt",
            )
        )
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"File not found: {path.as_posix()}",
                why="The path does not point to an existing app file.",
                fix="Check the path or run from your project root.",
                example="n3 app.ai fmt",
            )
        ) from err
    formatted = format_source(source)
    if check_only:
        if formatted == source:
            print("OK")
            return 0
        print("Needs formatting")
        return 1
    if formatted == source:
        print("Already formatted")
        return 0
    path.write_text(formatted, encoding="utf-8")
    print("Formatted")
    return 0
