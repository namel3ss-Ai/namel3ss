from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


def parse_ai_input_clause(parser, *, context: str) -> tuple[object, str]:
    if _match_ident_value(parser, "structured") is not None:
        parser._expect("INPUT", f"Expected 'input' after 'structured' in {context}")
        _expect_ident_value(parser, "from", f"Expected 'from' after structured input in {context}")
        input_expr = parser._parse_expression()
        return input_expr, "structured"
    if parser._match("TEXT"):
        parser._expect("INPUT", f"Expected 'input' after 'text' in {context}")
    else:
        parser._expect("INPUT", f"Expected 'input' in {context}")
    parser._match("COLON")
    input_expr = parser._parse_expression()
    return input_expr, "text"


def _match_ident_value(parser, value: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    return None


def _expect_ident_value(parser, value: str, message: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    raise Namel3ssError(message, line=tok.line, column=tok.column)


__all__ = ["parse_ai_input_clause"]
