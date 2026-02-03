from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.expr.common import read_attr_name


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
    clause = None
    if tok.type == "IDENT" and tok.value == "visibility":
        clause = "visibility"
    elif tok.type == "WHEN":
        clause = "when"
    elif tok.type == "IDENT" and tok.value == "visible_when":
        clause = "visible_when"
    if clause is None:
        return None
    parser._advance()
    if clause == "visibility":
        parser._expect("IS", "Expected 'is' after visibility")
    elif clause == "when":
        parser._expect("IS", "Expected 'is' after when")
    else:
        parser._expect("IS", "Expected 'is' after visible_when")
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


def _is_visibility_rule_start(parser) -> bool:
    tok = parser._current()
    return tok.type == "IDENT" and tok.value == "only"


def _parse_visibility_rule_line(parser, *, allow_pattern_params: bool = False) -> ast.VisibilityRule:
    only_tok = parser._current()
    if only_tok.type != "IDENT" or only_tok.value != "only":
        raise Namel3ssError("Expected 'only when' visibility rule", line=only_tok.line, column=only_tok.column)
    parser._advance()
    parser._expect("WHEN", "Expected 'when' after only")
    try:
        path = _parse_state_path_relaxed(parser)
    except Namel3ssError as err:
        raise Namel3ssError(
            "Visibility rule requires state.<path> is <value>.",
            line=err.line,
            column=err.column,
        ) from err
    parser._expect("IS", "Expected 'is' after state path")
    value = _parse_visibility_rule_value(parser, allow_pattern_params=allow_pattern_params)
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Visibility rule only supports a literal value.",
            line=extra.line,
            column=extra.column,
        )
    return ast.VisibilityRule(path=path, value=value, line=only_tok.line, column=only_tok.column)


def _parse_visibility_rule_value(parser, *, allow_pattern_params: bool) -> ast.Literal:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "NUMBER":
        parser._advance()
        return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
    if tok.type == "BOOLEAN":
        parser._advance()
        return ast.Literal(value=bool(tok.value), line=tok.line, column=tok.column)
    if tok.type == "IDENT":
        parser._advance()
        return ast.Literal(value=str(tok.value), line=tok.line, column=tok.column)
    raise Namel3ssError(
        "Visibility rule requires a text, number, or boolean value.",
        line=tok.line,
        column=tok.column,
    )


def _parse_visibility_rule_block(parser, *, allow_pattern_params: bool = False) -> ast.VisibilityRule | None:
    if parser._current().type != "NEWLINE":
        return None
    next_pos = parser.position + 1
    if next_pos >= len(parser.tokens):
        return None
    if parser.tokens[next_pos].type != "INDENT":
        return None
    peek_pos = next_pos + 1
    while peek_pos < len(parser.tokens) and parser.tokens[peek_pos].type == "NEWLINE":
        peek_pos += 1
    if peek_pos >= len(parser.tokens):
        return None
    peek_tok = parser.tokens[peek_pos]
    if not (peek_tok.type == "IDENT" and peek_tok.value == "only"):
        return None
    parser._advance()  # consume NEWLINE
    parser._advance()  # consume INDENT
    rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if rule is not None:
            tok = parser._current()
            raise Namel3ssError(
                "Visibility blocks may only declare one only-when rule.",
                line=tok.line,
                column=tok.column,
            )
        if not _is_visibility_rule_start(parser):
            tok = parser._current()
            raise Namel3ssError(
                "Visibility blocks may only declare an only-when rule.",
                line=tok.line,
                column=tok.column,
            )
        rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of visibility block")
    if rule is None:
        tok = parser._current()
        raise Namel3ssError("Visibility block has no rule", line=tok.line, column=tok.column)
    return rule


def _validate_visibility_combo(
    visibility: ast.StatePath | ast.PatternParamRef | None,
    visibility_rule: ast.VisibilityRule | None,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if visibility is not None and visibility_rule is not None:
        raise Namel3ssError(
            "Visibility cannot combine visibility clauses with only-when rules.",
            line=line,
            column=column,
        )


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
    "_match_ident_value",
    "_reject_list_transforms",
    "_parse_visibility_clause",
    "_parse_string_value",
    "_parse_optional_string_value",
    "_parse_reference_name_value",
    "_parse_state_path_value",
    "_parse_state_path_value_relaxed",
    "_parse_boolean_value",
    "_parse_number_value",
    "_is_visibility_rule_start",
    "_parse_visibility_rule_line",
    "_parse_visibility_rule_block",
    "_validate_visibility_combo",
    "_is_param_ref",
    "_parse_param_ref",
]
