from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.core.helpers import parse_reference_name


def parse_update(parser) -> ast.Update:
    update_tok = parser._advance()
    record_name = parse_reference_name(parser, context="record")
    parser._expect("WHERE", "Expected 'where' in update statement")
    predicate = parser._parse_expression()
    if not parser._match("SET"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Update statement is missing 'set'.",
                why="Update assignments must follow a set block.",
                fix='Use `update "Record" where <predicate> set:` with field assignments.',
                example='update "Order" where id is 1 set:\n  status is "Fulfilled"',
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._expect("COLON", "Expected ':' after set")
    parser._expect("NEWLINE", "Expected newline after set")
    parser._expect("INDENT", "Expected indented update assignments")

    updates: List[ast.UpdateField] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field_tok = parser._current()
        field_name = parse_reference_name(parser, context="field")
        parser._expect("IS", "Expected 'is' after field name")
        expr = parser._parse_expression()
        updates.append(ast.UpdateField(name=field_name, expression=expr, line=field_tok.line, column=field_tok.column))
        parser._match("NEWLINE")

    parser._expect("DEDENT", "Expected end of update assignments")
    while parser._match("NEWLINE"):
        pass

    if not updates:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Update statement has no assignments.",
                why="Update needs at least one field assignment to apply.",
                fix="Add one or more field assignments under set:.",
                example='update "Order" where id is 1 set:\n  status is "Fulfilled"',
            ),
            line=tok.line,
            column=tok.column,
        )

    return ast.Update(record_name=record_name, predicate=predicate, updates=updates, line=update_tok.line, column=update_tok.column)


__all__ = ["parse_update"]
