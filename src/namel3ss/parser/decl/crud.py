from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_crud_decl(parser) -> ast.CrudDefinition:
    crud_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected record name string")
    if parser._match("COLON"):
        raise Namel3ssError(
            build_guidance_message(
                what="Crud declaration does not use a colon.",
                why="Crud is a single line declaration that expands to routes.",
                fix="Remove the colon after the record name.",
                example='crud "User"',
            ),
            line=crud_tok.line,
            column=crud_tok.column,
        )
    next_tok = parser._current()
    if next_tok.type not in {"NEWLINE", "EOF", "DEDENT"}:
        raise Namel3ssError(
            build_guidance_message(
                what="Crud declaration has extra tokens.",
                why="Crud only accepts a record name on a single line.",
                fix="Keep the crud declaration on one line.",
                example='crud "User"',
            ),
            line=next_tok.line,
            column=next_tok.column,
        )
    return ast.CrudDefinition(record_name=name_tok.value, line=crud_tok.line, column=crud_tok.column)


__all__ = ["parse_crud_decl"]
