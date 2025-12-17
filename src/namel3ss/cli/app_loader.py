from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path


def load_program(path_str: str) -> tuple[object, str]:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError("Input file must have .ai extension")
    apply_dotenv(load_dotenv_for_path(str(path)))
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(f"File not found: {path}") from err
    ast_program = parse(source)
    program_ir = lower_program(ast_program)
    return program_ir, source
