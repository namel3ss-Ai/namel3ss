from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core.helpers import parse_reference_name


def parse_create(parser) -> ast.Create:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    if not parser._match("WITH"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Create statement is missing 'with'.",
                why="`with` introduces the values used to create the record.",
                fix='Use `create "<Record>" with <values> as <var>`.',
                example='create "Order" with state.order as order',
            ),
            line=tok.line,
            column=tok.column,
        )
    values_expr = parser._parse_expression()
    if not parser._match("AS"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Create statement is missing 'as'.",
                why="`as` names the variable that receives the saved record.",
                fix='Use `create "<Record>" with <values> as <var>`.',
                example='create "Order" with state.order as order',
            ),
            line=tok.line,
            column=tok.column,
        )
    target_tok = parser._current()
    if target_tok.type != "IDENT":
        raise Namel3ssError(
            build_guidance_message(
                what="Create statement is missing a target variable.",
                why="`as <var>` names the variable that receives the saved record.",
                fix='Provide a variable name after `as`, e.g. `as order`.',
                example='create "Order" with state.order as order',
            ),
            line=target_tok.line,
            column=target_tok.column,
        )
    parser._advance()
    return ast.Create(record_name=record_name, values=values_expr, target=target_tok.value, line=tok.line, column=tok.column)


__all__ = ["parse_create"]
