from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.expr.common import read_attr_name


def _parse_string_value(parser, *, allow_pattern_params: bool, context: str) -> str | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    tok = parser._expect("STRING", f"Expected {context} string")
    return tok.value


def _parse_optional_string_value(parser, *, allow_pattern_params: bool) -> str | ast.PatternParamRef | None:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    return None


def _parse_reference_name_value(parser, *, allow_pattern_params: bool, context: str) -> str | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    from namel3ss.parser.core.helpers import parse_reference_name

    return parse_reference_name(parser, context=context)


def _parse_state_path_value(parser, *, allow_pattern_params: bool) -> ast.StatePath | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    return parser._parse_state_path()


def _parse_state_path_value_relaxed(parser, *, allow_pattern_params: bool) -> ast.StatePath | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    return _parse_state_path_relaxed(parser)


def _parse_state_path_relaxed(parser) -> ast.StatePath:
    state_tok = parser._expect("STATE", "Expected 'state'")
    path: list[str] = []
    if parser._match("DOT"):
        path.append(read_attr_name(parser, context="identifier after '.'"))
    else:
        path.append(read_attr_name(parser, context="state path"))
    while parser._match("DOT"):
        path.append(read_attr_name(parser, context="identifier after '.'"))
    return ast.StatePath(path=path, line=state_tok.line, column=state_tok.column)


def _parse_boolean_value(parser, *, allow_pattern_params: bool) -> bool | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    tok = parser._expect("BOOLEAN", "Expected true or false")
    return bool(tok.value)


def _parse_number_value(parser, *, allow_pattern_params: bool) -> int | float | ast.PatternParamRef:
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    tok = parser._expect("NUMBER", "Expected number")
    return tok.value


def _is_param_ref(parser) -> bool:
    tok = parser._current()
    return tok.type == "PARAM"


def _parse_param_ref(parser) -> ast.PatternParamRef:
    tok = parser._current()
    if tok.type != "PARAM":
        raise Namel3ssError("Expected param.<name>", line=tok.line, column=tok.column)
    parser._advance()
    parser._expect("DOT", "Expected '.' after param")
    name_tok = parser._expect("IDENT", "Expected parameter name")
    return ast.PatternParamRef(name=name_tok.value, line=tok.line, column=tok.column)


__all__ = [
    "_parse_string_value",
    "_parse_optional_string_value",
    "_parse_reference_name_value",
    "_parse_state_path_value",
    "_parse_state_path_value_relaxed",
    "_parse_state_path_relaxed",
    "_parse_boolean_value",
    "_parse_number_value",
    "_is_param_ref",
    "_parse_param_ref",
]
