from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_repeat(parser) -> ast.Repeat:
    rep_tok = parser._advance()
    parser._expect("UP", "Expected 'up' in repeat statement")
    parser._expect("TO", "Expected 'to' in repeat statement")
    count_expr = parser._parse_expression()
    parser._expect("TIMES", "Expected 'times' after repeat count")
    parser._expect("COLON", "Expected ':' after repeat header")
    body = parser._parse_block()
    return ast.Repeat(count=count_expr, body=body, line=rep_tok.line, column=rep_tok.column)


__all__ = ["parse_repeat"]
