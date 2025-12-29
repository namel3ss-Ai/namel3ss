from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_for_each(parser) -> ast.ForEach:
    for_tok = parser._advance()
    parser._expect("EACH", "Expected 'each' after 'for'")
    name_tok = parser._expect("IDENT", "Expected loop variable name")
    parser._expect("IN", "Expected 'in' in for-each loop")
    iterable = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after for-each header")
    body = parser._parse_block()
    return ast.ForEach(name=name_tok.value, iterable=iterable, body=body, line=for_tok.line, column=for_tok.column)


__all__ = ["parse_for_each"]
