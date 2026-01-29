from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import _parse_reference_name_value, _parse_state_path_value, _parse_string_value
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_chart_header(parser, *, allow_pattern_params: bool = False) -> tuple[str | None, ast.StatePath | ast.PatternParamRef | None]:
    if parser._match("IS"):
        record_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="record")
        return record_name, None
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == "from":
        parser._advance()
        parser._expect("IS", "Expected 'is' after chart from")
        source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
        return None, source
    raise Namel3ssError(
        'Chart must use is "Record" or from is state.<path>',
        line=tok.line,
        column=tok.column,
    )


def parse_chart_block(parser, *, allow_pattern_params: bool = False) -> tuple[str | None, str | None, str | None, str | None]:
    parser._expect("NEWLINE", "Expected newline after chart header")
    parser._expect("INDENT", "Expected indented chart block")
    chart_type = None
    x = None
    y = None
    explain = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "type":
            if chart_type is not None:
                raise Namel3ssError("Chart type is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after type")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError("Chart type must be text", line=value_tok.line, column=value_tok.column)
            parser._advance()
            chart_type = str(value_tok.value)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "x":
            if x is not None:
                raise Namel3ssError("Chart x mapping is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after x")
            x = _parse_chart_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "y":
            if y is not None:
                raise Namel3ssError("Chart y mapping is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after y")
            y = _parse_chart_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "explain":
            if explain is not None:
                raise Namel3ssError("Chart explain is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after explain")
            explain = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="explain")
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(f"Unknown chart setting '{tok.value}'", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of chart block")
    if chart_type is None and x is None and y is None and explain is None:
        raise Namel3ssError("Chart block has no entries", line=parser._current().line, column=parser._current().column)
    return chart_type, x, y, explain


def _parse_chart_field_name(parser) -> str:
    tok = parser._current()
    if tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return str(tok.value)
    if isinstance(tok.value, str) and is_keyword(tok.value):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise Namel3ssError(guidance, line=tok.line, column=tok.column, details=details)
    raise Namel3ssError("Expected field name", line=tok.line, column=tok.column)


__all__ = ["parse_chart_block", "parse_chart_header"]
