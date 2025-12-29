from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.expr.common import read_attr_name


def parse_state_path(parser) -> ast.StatePath:
    state_tok = parser._expect("STATE", "Expected 'state'")
    path: List[str] = []
    while parser._match("DOT"):
        path.append(read_attr_name(parser, context="identifier after '.'"))
    if not path:
        raise Namel3ssError("Expected state path after 'state'", line=state_tok.line, column=state_tok.column)
    return ast.StatePath(path=path, line=state_tok.line, column=state_tok.column)


__all__ = ["parse_state_path"]
