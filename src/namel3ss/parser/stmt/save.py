from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.core.helpers import parse_reference_name


def parse_save(parser) -> ast.Save:
    tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    return ast.Save(record_name=record_name, line=tok.line, column=tok.column)


__all__ = ["parse_save"]
