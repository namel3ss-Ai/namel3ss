from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.core.helpers import parse_reference_name


def parse_find(parser) -> ast.Find:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("WHERE", "Expected 'where' in find statement")
    predicate = parser._parse_expression()
    return ast.Find(record_name=record_name, predicate=predicate, line=tok.line, column=tok.column)


__all__ = ["parse_find"]
