from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_await_stmt(parser) -> ast.Await:
    await_tok = parser._advance()
    name_tok = parser._current()
    if name_tok.type not in {"IDENT", "INPUT"}:
        raise Namel3ssError("Expected async variable name after await", line=name_tok.line, column=name_tok.column)
    parser._advance()
    return ast.Await(name=str(name_tok.value), line=await_tok.line, column=await_tok.column)


__all__ = ["parse_await_stmt"]
