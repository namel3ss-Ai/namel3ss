from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.grouping import parse_braced_items
from namel3ss.parser.decl.page import parse_page_item
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_ui_pattern_decl(parser) -> ast.UIPatternDecl:
    pattern_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected pattern name string")
    if isinstance(name_tok.value, str) and is_keyword(name_tok.value):
        raise Namel3ssError(
            f"'{name_tok.value}' is a reserved keyword.",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("COLON", "Expected ':' after pattern name")
    parser._expect("NEWLINE", "Expected newline after pattern header")
    parser._expect("INDENT", "Expected indented pattern body")
    parameters: list[ast.PatternParam] = []
    seen_params: set[str] = set()
    saw_parameters = False
    items: list[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "parameters":
            if saw_parameters:
                raise Namel3ssError("Parameters are declared more than once", line=tok.line, column=tok.column)
            saw_parameters = True
            parameters = _parse_parameters_block(parser, seen_params)
            continue
        items.append(parse_page_item(parser, allow_tabs=True, allow_overlays=True, allow_pattern_params=True))
    parser._expect("DEDENT", "Expected end of pattern body")
    if not items:
        raise Namel3ssError("Pattern has no entries", line=pattern_tok.line, column=pattern_tok.column)
    return ast.UIPatternDecl(
        name=name_tok.value,
        parameters=parameters,
        items=items,
        line=pattern_tok.line,
        column=pattern_tok.column,
    )


def _parse_parameters_block(parser, seen_params: set[str]) -> list[ast.PatternParam]:
    params_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after parameters")
    params: list[ast.PatternParam] = []
    if parser._current().type == "LBRACE":
        params.extend(parse_braced_items(parser, context="parameters", parse_item=lambda: _parse_param_entry(parser, seen_params), allow_empty=True))
        parser._match("NEWLINE")
    else:
        parser._expect("NEWLINE", "Expected newline after parameters")
        parser._expect("INDENT", "Expected indented parameters block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            params.append(_parse_param_entry(parser, seen_params))
            if parser._match("NEWLINE"):
                continue
        parser._expect("DEDENT", "Expected end of parameters block")
    if not params:
        raise Namel3ssError("Parameters block has no entries", line=params_tok.line, column=params_tok.column)
    return params


def _parse_param_entry(parser, seen_params: set[str]) -> ast.PatternParam:
    name_tok = parser._current()
    if name_tok.type != "IDENT":
        raise Namel3ssError("Expected parameter name", line=name_tok.line, column=name_tok.column)
    if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
        guidance, details = reserved_identifier_diagnostic(name_tok.value)
        raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
    param_name = name_tok.value
    parser._advance()
    if param_name in seen_params:
        raise Namel3ssError(
            f"Parameter '{param_name}' is duplicated",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("IS", "Expected 'is' after parameter name")
    kind = _parse_param_kind(parser)
    optional = False
    default = None
    while True:
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "optional":
            optional = True
            parser._advance()
            continue
        if tok.type == "IDENT" and tok.value == "default":
            parser._advance()
            parser._expect("IS", "Expected 'is' after default")
            default = _parse_param_value(parser)
            _validate_param_value(kind, default, line=tok.line, column=tok.column)
            optional = True
            continue
        break
    param = ast.PatternParam(
        name=param_name,
        kind=kind,
        optional=optional,
        default=default,
        line=name_tok.line,
        column=name_tok.column,
    )
    seen_params.add(param_name)
    return param


def _parse_param_kind(parser) -> str:
    tok = parser._current()
    if tok.type in {"TEXT", "TYPE_STRING"}:
        parser._advance()
        return "text"
    if tok.type in {"TYPE_NUMBER", "TYPE_INT"}:
        parser._advance()
        return "number"
    if tok.type == "TYPE_BOOLEAN":
        parser._advance()
        return "boolean"
    if tok.type == "RECORD":
        parser._advance()
        return "record"
    if tok.type == "PAGE":
        parser._advance()
        return "page"
    raise Namel3ssError("Unsupported parameter type", line=tok.line, column=tok.column)


def _parse_param_value(parser) -> object:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    if tok.type == "NUMBER":
        parser._advance()
        return tok.value
    if tok.type == "BOOLEAN":
        parser._advance()
        return bool(tok.value)
    raise Namel3ssError("Expected parameter default value", line=tok.line, column=tok.column)


def _validate_param_value(kind: str, value: object, *, line: int | None, column: int | None) -> None:
    if kind in {"text", "record", "page"} and isinstance(value, str):
        return
    if kind == "number" and isinstance(value, (int, float)):
        return
    if kind == "boolean" and isinstance(value, bool):
        return
    raise Namel3ssError(
        f"Default value does not match {kind} parameter type",
        line=line,
        column=column,
    )


__all__ = ["parse_ui_pattern_decl"]
