from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.format.formatter import format_source


def run_format(path_str: str, check_only: bool) -> int:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError("Input file must have .ai extension")
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"File not found: {path}") from err
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
