from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.utils.numbers import decimal_is_int, to_decimal


def parse_repeat(parser) -> ast.Repeat:
    rep_tok = parser._advance()
    if _match_word(parser, "while"):
        condition = parser._parse_expression()
        _expect_word(parser, "limit")
        limit_tok = parser._expect("NUMBER", "Expected loop limit number")
        limit_value = to_decimal(limit_tok.value)
        if not decimal_is_int(limit_value):
            raise Namel3ssError("Loop limit must be an integer", line=limit_tok.line, column=limit_tok.column)
        limit_int = int(limit_value)
        if limit_int <= 0:
            raise Namel3ssError("Loop limit must be greater than zero", line=limit_tok.line, column=limit_tok.column)
        parser._expect("COLON", "Expected ':' after loop limit")
        body = parser._parse_block()
        return ast.RepeatWhile(
            condition=condition,
            limit=limit_int,
            body=body,
            limit_line=limit_tok.line,
            limit_column=limit_tok.column,
            line=rep_tok.line,
            column=rep_tok.column,
        )
    parser._expect("UP", "Expected 'up' in repeat statement")
    parser._expect("TO", "Expected 'to' in repeat statement")
    count_expr = parser._parse_expression()
    parser._expect("TIMES", "Expected 'times' after repeat count")
    parser._expect("COLON", "Expected ':' after repeat header")
    body = parser._parse_block()
    return ast.Repeat(count=count_expr, body=body, line=rep_tok.line, column=rep_tok.column)


def _match_word(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        return False
    parser._advance()
    return True


def _expect_word(parser, value: str) -> None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        raise Namel3ssError(f"Expected '{value}'", line=tok.line, column=tok.column)
    parser._advance()


__all__ = ["parse_repeat"]
