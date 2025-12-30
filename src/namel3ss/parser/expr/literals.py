from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_number_literal(parser) -> ast.Literal:
    tok = parser._current()
    parser._advance()
    return ast.Literal(value=tok.value, line=tok.line, column=tok.column)


def parse_string_literal(parser) -> ast.Literal:
    tok = parser._current()
    parser._advance()
    return ast.Literal(value=tok.value, line=tok.line, column=tok.column)


def parse_boolean_literal(parser) -> ast.Literal:
    tok = parser._current()
    parser._advance()
    return ast.Literal(value=tok.value, line=tok.line, column=tok.column)


def parse_null_literal(parser) -> ast.Literal:
    tok = parser._current()
    parser._advance()
    return ast.Literal(value=None, line=tok.line, column=tok.column)


__all__ = ["parse_number_literal", "parse_string_literal", "parse_boolean_literal", "parse_null_literal"]
