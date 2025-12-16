from __future__ import annotations

from namel3ss.ast import nodes as ast


def parse_let(parser) -> ast.Let:
    let_tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected identifier after 'let'")
    parser._expect("IS", "Expected 'is' in declaration")
    expr = parser._parse_expression()
    constant = False
    if parser._match("CONSTANT"):
        constant = True
    return ast.Let(name=name_tok.value, expression=expr, constant=constant, line=let_tok.line, column=let_tok.column)


def parse_set(parser) -> ast.Set:
    set_tok = parser._advance()
    target = parser._parse_target()
    parser._expect("IS", "Expected 'is' in assignment")
    expr = parser._parse_expression()
    return ast.Set(target=target, expression=expr, line=set_tok.line, column=set_tok.column)
