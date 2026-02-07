from __future__ import annotations

from decimal import Decimal

from namel3ss.ast.responsive import ResponsiveBreakpoint, ResponsiveDecl
from namel3ss.errors.base import Namel3ssError


def parse_responsive_decl(parser) -> ResponsiveDecl:
    tok = parser._expect("IDENT", "Expected responsive declaration")
    if tok.value != "responsive":
        raise Namel3ssError("Expected responsive declaration", line=tok.line, column=tok.column)
    parser._expect("COLON", "Expected ':' after responsive")
    parser._expect("NEWLINE", "Expected newline after responsive")
    parser._expect("INDENT", "Expected indented responsive block")

    breakpoints: list[ResponsiveBreakpoint] | None = None

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._expect("IDENT", "Expected responsive field")
        if key_tok.value != "breakpoints":
            raise Namel3ssError(
                f'Unknown responsive field "{key_tok.value}".',
                line=key_tok.line,
                column=key_tok.column,
            )
        if breakpoints is not None:
            raise Namel3ssError(
                "Responsive breakpoints are already declared.",
                line=key_tok.line,
                column=key_tok.column,
            )
        parser._expect("COLON", "Expected ':' after breakpoints")
        breakpoints = _parse_breakpoints_block(parser)

    parser._expect("DEDENT", "Expected end of responsive block")
    while parser._match("NEWLINE"):
        continue

    if not breakpoints:
        raise Namel3ssError("Responsive block requires at least one breakpoint.", line=tok.line, column=tok.column)
    return ResponsiveDecl(breakpoints=breakpoints, line=tok.line, column=tok.column)


def _parse_breakpoints_block(parser) -> list[ResponsiveBreakpoint]:
    parser._expect("NEWLINE", "Expected newline after breakpoints")
    parser._expect("INDENT", "Expected indented breakpoints block")
    entries: list[ResponsiveBreakpoint] = []
    names: set[str] = set()

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", "Expected breakpoint name")
        name = str(name_tok.value)
        if name in names:
            raise Namel3ssError(
                f'Duplicate breakpoint "{name}".',
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("COLON", "Expected ':' after breakpoint name")
        width = _parse_breakpoint_width(parser)
        names.add(name)
        entries.append(ResponsiveBreakpoint(name=name, width=width, line=name_tok.line, column=name_tok.column))
        parser._match("NEWLINE")

    parser._expect("DEDENT", "Expected end of breakpoints block")
    return entries


def _parse_breakpoint_width(parser) -> int:
    width_tok = parser._expect("NUMBER", "Expected breakpoint width")
    value = width_tok.value
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise Namel3ssError("Breakpoint width must be an integer.", line=width_tok.line, column=width_tok.column)
        width = int(value)
    else:
        width = int(value)
    if width < 0:
        raise Namel3ssError("Breakpoint width cannot be negative.", line=width_tok.line, column=width_tok.column)
    return width


__all__ = ["parse_responsive_decl"]
