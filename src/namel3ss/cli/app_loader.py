from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.config.dotenv import apply_dotenv, load_dotenv_for_path


def load_program(path_str: str, allow_legacy_type_aliases: bool = True) -> tuple[object, str]:
    path = Path(path_str)
    if path.suffix != ".ai":
        raise Namel3ssError(
            f"App file not found: {path_str}\nWhy: namel3ss apps use the .ai extension.\nFix: run `n3 <app.ai> check` from your project folder."
        )
    apply_dotenv(load_dotenv_for_path(str(path)))
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise Namel3ssError(
            f"App file not found: {path}\nWhy: no app.ai exists at this path.\nFix: cd into your project folder or run `n3 {path} check`."
        ) from err
    ast_program = parse(source, allow_legacy_type_aliases=allow_legacy_type_aliases)
    program_ir = lower_program(ast_program)
    return program_ir, source
