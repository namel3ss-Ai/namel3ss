from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import _parse_string_value


def parse_image_role_block(
    parser,
    *,
    line: int | None,
    column: int | None,
    allow_pattern_params: bool = False,
) -> str:
    parser._expect("NEWLINE", "Expected newline after image")
    parser._expect("INDENT", "Expected indented image block")
    role: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        field = tok.value
        if field != "role":
            raise Namel3ssError("Image blocks may only declare role", line=tok.line, column=tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after role")
        if role is not None:
            raise Namel3ssError("Image role is already declared", line=tok.line, column=tok.column)
        role = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="role")
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of image block")
    if role is None:
        raise Namel3ssError("Image role block is empty", line=line, column=column)
    return role


__all__ = ["parse_image_role_block"]
