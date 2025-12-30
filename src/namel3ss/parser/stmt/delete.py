from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.core.helpers import parse_reference_name


def parse_delete(parser) -> ast.Delete:
    delete_tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("WHERE", "Expected 'where' in delete statement")
    predicate = parser._parse_expression()
    return ast.Delete(record_name=record_name, predicate=predicate, line=delete_tok.line, column=delete_tok.column)


__all__ = ["parse_delete"]
