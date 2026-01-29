from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def _match_ident_value(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return True
    return False


def _reject_list_transforms(expr: ast.Expression | None) -> None:
    if expr is None:
        return
    if isinstance(expr, (ast.ListMapExpr, ast.ListFilterExpr, ast.ListReduceExpr)):
        raise Namel3ssError(
            "Pages are declarative; list transforms are not allowed in page expressions",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.CallFunctionExpr):
        for arg in expr.arguments:
            _reject_list_transforms(arg.value)
        return
    if isinstance(expr, ast.UnaryOp):
        _reject_list_transforms(expr.operand)
        return
    if isinstance(expr, ast.BinaryOp):
        _reject_list_transforms(expr.left)
        _reject_list_transforms(expr.right)
        return
    if isinstance(expr, ast.Comparison):
        _reject_list_transforms(expr.left)
        _reject_list_transforms(expr.right)
        return
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            _reject_list_transforms(item)
        return
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            _reject_list_transforms(entry.key)
            _reject_list_transforms(entry.value)
        return
    if isinstance(expr, ast.ListOpExpr):
        _reject_list_transforms(expr.target)
        if expr.value is not None:
            _reject_list_transforms(expr.value)
        if expr.index is not None:
            _reject_list_transforms(expr.index)
        return
    if isinstance(expr, ast.MapOpExpr):
        _reject_list_transforms(expr.target)
        if expr.key is not None:
            _reject_list_transforms(expr.key)
        if expr.value is not None:
            _reject_list_transforms(expr.value)
        return


def _parse_visibility_clause(parser, *, allow_pattern_params: bool = False) -> ast.StatePath | ast.PatternParamRef | None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "visibility":
        return None
    parser._advance()
    parser._expect("IS", "Expected 'is' after visibility")
    if allow_pattern_params and _is_param_ref(parser):
        path = _parse_param_ref(parser)
    else:
        try:
            path = parser._parse_state_path()
        except Namel3ssError as err:
            raise Namel3ssError(
                "Visibility requires state.<path>.",
                line=err.line,
                column=err.column,
            )
    if parser._current().type not in {"NEWLINE", "COLON", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Visibility only supports a state path.",
            line=extra.line,
            column=extra.column,
        )
    return path


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
    "_match_ident_value",
    "_reject_list_transforms",
    "_parse_visibility_clause",
    "_parse_string_value",
    "_parse_optional_string_value",
    "_parse_reference_name_value",
    "_parse_state_path_value",
    "_parse_boolean_value",
    "_parse_number_value",
    "_is_param_ref",
    "_parse_param_ref",
]
