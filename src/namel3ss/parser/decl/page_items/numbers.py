from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.decl.page_common import _parse_visibility_clause


def parse_number_item(parser, tok) -> ast.NumberItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser)
    parser._expect("COLON", "Expected ':' after number")
    entries: list[ast.NumberEntry] = []
    parser._expect("NEWLINE", "Expected newline after number")
    if not parser._match("INDENT"):
        raise Namel3ssError("Number block has no entries", line=tok.line, column=tok.column)
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        entry_tok = parser._current()
        if entry_tok.type == "IDENT" and entry_tok.value == "count":
            parser._advance()
            of_tok = parser._current()
            if of_tok.type not in {"IDENT"} or of_tok.value != "of":
                raise Namel3ssError("Expected 'of' after count", line=of_tok.line, column=of_tok.column)
            parser._advance()
            record_name = parse_reference_name(parser, context="record")
            as_tok = parser._current()
            if as_tok.type not in {"IDENT", "AS"} or as_tok.value != "as":
                raise Namel3ssError("Expected 'as' after record name", line=as_tok.line, column=as_tok.column)
            parser._advance()
            label_tok = parser._expect("STRING", "Expected label string for count")
            entries.append(
                ast.NumberEntry(
                    kind="count",
                    record_name=record_name,
                    label=label_tok.value,
                    line=entry_tok.line,
                    column=entry_tok.column,
                )
            )
            parser._match("NEWLINE")
            continue
        if entry_tok.type == "STRING":
            parser._advance()
            phrase = entry_tok.value
        else:
            parts: list[str] = []
            while parser._current().type not in {"NEWLINE", "DEDENT"}:
                parts.append(parser._current().value)
                parser._advance()
            phrase = " ".join(parts).strip()
            if not phrase:
                raise Namel3ssError("Number phrase is empty", line=entry_tok.line, column=entry_tok.column)
        entries.append(ast.NumberEntry(kind="phrase", value=phrase, line=entry_tok.line, column=entry_tok.column))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of number block")
    if not entries:
        raise Namel3ssError("Number block has no entries", line=tok.line, column=tok.column)
    return ast.NumberItem(entries=entries, visibility=visibility, line=tok.line, column=tok.column)


__all__ = ["parse_number_item"]
