from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.tool import _old_tool_syntax_message
from namel3ss.parser.expr.calls import looks_like_tool_call, parse_tool_call_expr


def parse_set(parser) -> ast.Set:
    set_tok = parser._advance()
    target = parser._parse_target()
    parser._expect("IS", "Expected 'is' in assignment")
    if parser._current().type == "CALL":
        raise Namel3ssError(_old_tool_syntax_message(), line=parser._current().line, column=parser._current().column)
    if looks_like_tool_call(parser):
        expr = parse_tool_call_expr(parser)
    else:
        expr = parser._parse_expression()
    return ast.Set(target=target, expression=expr, line=set_tok.line, column=set_tok.column)


__all__ = ["parse_set"]
