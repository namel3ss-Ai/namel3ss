from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_try(parser) -> ast.TryCatch:
    try_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after try")
    try_body = parser._parse_block()
    if not parser._match("WITH"):
        tok = parser._current()
        raise Namel3ssError("Expected 'with' introducing catch", line=tok.line, column=tok.column)
    parser._expect("CATCH", "Expected 'catch' after 'with'")
    var_tok = parser._expect("IDENT", "Expected catch variable name")
    parser._expect("COLON", "Expected ':' after catch clause")
    catch_body = parser._parse_block()
    return ast.TryCatch(try_body=try_body, catch_var=var_tok.value, catch_body=catch_body, line=try_tok.line, column=try_tok.column)


__all__ = ["parse_try"]
