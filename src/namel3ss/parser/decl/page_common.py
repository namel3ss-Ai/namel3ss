from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.diagnostics_mode import DEBUG_ONLY_CATEGORIES, normalize_debug_only_category
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.visibility_expr import parse_visibility_expression
from namel3ss.parser.decl.page_value_parsers import (
    _is_param_ref,
    _parse_boolean_value,
    _parse_number_value,
    _parse_optional_string_value,
    _parse_param_ref,
    _parse_reference_name_value,
    _parse_state_path_relaxed,
    _parse_state_path_value,
    _parse_state_path_value_relaxed,
    _parse_string_value,
)
from namel3ss.parser.decl.page_style import _parse_style_hooks_block, _parse_variant_line


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


def _is_visibility_clause_start(parser) -> bool:
    tok = parser._current()
    if tok.type == "IDENT" and tok.value in {"visibility", "visible_when"}:
        return True
    if tok.type == "WHEN":
        return True
    if tok.type == "IDENT" and tok.value == "visible":
        next_tok = parser.tokens[parser.position + 1] if parser.position + 1 < len(parser.tokens) else tok
        return next_tok.type == "WHEN"
    return False


def _parse_visibility_clause(parser, *, allow_pattern_params: bool = False) -> ast.Expression | ast.PatternParamRef | None:
    if not _is_visibility_clause_start(parser):
        return None
    tok = parser._current()
    clause: str | None = None
    if tok.type == "IDENT" and tok.value == "visibility":
        clause = "visibility"
        parser._advance()
    elif tok.type == "WHEN":
        clause = "when"
        parser._advance()
    elif tok.type == "IDENT" and tok.value == "visible_when":
        clause = "visible_when"
        parser._advance()
    elif tok.type == "IDENT" and tok.value == "visible":
        clause = "visible_when_phrase"
        parser._advance()
        parser._expect("WHEN", "Expected 'when' after visible")
    if clause is None:
        return None
    if clause == "visibility":
        parser._expect("IS", "Expected 'is' after visibility")
    elif clause == "when":
        parser._match("IS")
    elif clause == "visible_when":
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", "Expected ':' or 'is' after visible_when")
    else:
        parser._match("IS")
    next_tok = parser.tokens[parser.position + 1] if parser.position + 1 < len(parser.tokens) else parser._current()
    if allow_pattern_params and _is_param_ref(parser) and next_tok.type in {"NEWLINE", "COLON", "DEDENT"}:
        path = _parse_param_ref(parser)
        return path
    expr = parse_visibility_expression(parser, allow_pattern_params=allow_pattern_params)
    if _is_visibility_clause_start(parser):
        dup = parser._current()
        raise Namel3ssError(
            "Visibility is declared more than once.",
            line=dup.line,
            column=dup.column,
        )
    if parser._current().type not in {"NEWLINE", "COLON", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Visibility expressions must end at the line boundary.",
            line=extra.line,
            column=extra.column,
        )
    return expr


def _is_show_when_clause_start(parser) -> bool:
    tok = parser._current()
    return tok.type == "IDENT" and tok.value == "show_when"


def _parse_show_when_clause(
    parser,
    *,
    allow_pattern_params: bool = False,
) -> ast.Expression | ast.PatternParamRef | None:
    if not _is_show_when_clause_start(parser):
        return None
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "show_when":
        raise Namel3ssError("Expected show_when metadata", line=tok.line, column=tok.column)
    parser._advance()
    if parser._match("COLON"):
        pass
    else:
        parser._expect("IS", "Expected ':' or 'is' after show_when")
    next_tok = parser.tokens[parser.position + 1] if parser.position + 1 < len(parser.tokens) else parser._current()
    if allow_pattern_params and _is_param_ref(parser) and next_tok.type in {"NEWLINE", "COLON", "DEDENT"}:
        path = _parse_param_ref(parser)
        return path
    expr = parse_visibility_expression(parser, allow_pattern_params=allow_pattern_params)
    if _is_show_when_clause_start(parser):
        dup = parser._current()
        raise Namel3ssError(
            "show_when is declared more than once.",
            line=dup.line,
            column=dup.column,
        )
    if parser._current().type not in {"NEWLINE", "COLON", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "show_when expressions must end at the line boundary.",
            line=extra.line,
            column=extra.column,
        )
    return expr


def _is_debug_only_start(parser) -> bool:
    tok = parser._current()
    return tok.type == "IDENT" and tok.value == "debug_only"


def _parse_debug_only_clause(parser) -> bool | str | None:
    if not _is_debug_only_start(parser):
        return None
    return _parse_debug_only_line(parser)


def _parse_debug_only_line(parser) -> bool | str:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "debug_only":
        raise Namel3ssError("Expected debug_only metadata", line=tok.line, column=tok.column)
    parser._advance()
    if parser._match("COLON"):
        pass
    else:
        parser._expect("IS", "Expected ':' or 'is' after debug_only")
    value_tok = parser._current()
    if value_tok.type == "BOOLEAN":
        parser._advance()
        value: bool | str = bool(value_tok.value)
    elif value_tok.type == "STRING":
        parser._advance()
        normalized = normalize_debug_only_category(value_tok.value)
        if normalized is None:
            allowed = ", ".join(DEBUG_ONLY_CATEGORIES)
            raise Namel3ssError(
                f"debug_only category must be one of: {allowed}.",
                line=value_tok.line,
                column=value_tok.column,
            )
        value = normalized
    else:
        raise Namel3ssError("debug_only must be a boolean literal or diagnostics category string", line=value_tok.line, column=value_tok.column)
    if parser._current().type not in {"NEWLINE", "DEDENT", "COLON"}:
        extra = parser._current()
        raise Namel3ssError("debug_only supports true, false, or a diagnostics category string", line=extra.line, column=extra.column)
    return value


def _is_diagnostics_start(parser) -> bool:
    tok = parser._current()
    return tok.type == "IDENT" and tok.value == "diagnostics"


def _parse_diagnostics_line(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "diagnostics":
        raise Namel3ssError("Expected diagnostics metadata", line=tok.line, column=tok.column)
    parser._advance()
    parser._expect("IS", "Expected 'is' after diagnostics")
    value_tok = parser._current()
    if value_tok.type != "BOOLEAN":
        raise Namel3ssError("diagnostics must be a boolean literal", line=value_tok.line, column=value_tok.column)
    parser._advance()
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError("diagnostics only supports true or false", line=extra.line, column=extra.column)
    return bool(value_tok.value)


def _is_visibility_rule_start(parser) -> bool:
    tok = parser._current()
    return tok.type == "IDENT" and tok.value == "only"


def _parse_visibility_rule_line(
    parser,
    *,
    allow_pattern_params: bool = False,
) -> ast.VisibilityRule | ast.VisibilityExpressionRule:
    only_tok = parser._current()
    if only_tok.type != "IDENT" or only_tok.value != "only":
        raise Namel3ssError("Expected 'only when' visibility rule", line=only_tok.line, column=only_tok.column)
    parser._advance()
    parser._expect("WHEN", "Expected 'when' after only")
    legacy_pos = parser.position
    try:
        path = _parse_state_path_relaxed(parser)
        parser._expect("IS", "Expected 'is' after state path")
        value = _parse_visibility_rule_value(parser, allow_pattern_params=allow_pattern_params)
        if parser._current().type not in {"NEWLINE", "DEDENT"}:
            raise Namel3ssError(
                "Visibility rule only supports a literal value.",
                line=parser._current().line,
                column=parser._current().column,
            )
        return ast.VisibilityRule(path=path, value=value, line=only_tok.line, column=only_tok.column)
    except Namel3ssError:
        parser.position = legacy_pos
    expression = parse_visibility_expression(parser, allow_pattern_params=allow_pattern_params)
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Visibility expressions must end at the line boundary.",
            line=extra.line,
            column=extra.column,
        )
    return ast.VisibilityExpressionRule(expression=expression, line=only_tok.line, column=only_tok.column)


def _parse_action_availability_rule_line(parser, *, allow_pattern_params: bool = False) -> ast.ActionAvailabilityRule:
    only_tok = parser._current()
    if only_tok.type != "IDENT" or only_tok.value != "only":
        raise Namel3ssError("Expected 'only when' action availability rule", line=only_tok.line, column=only_tok.column)
    parser._advance()
    parser._expect("WHEN", "Expected 'when' after only")
    try:
        path = _parse_state_path_relaxed(parser)
    except Namel3ssError as err:
        raise Namel3ssError(
            "Action availability requires state.<path> is <value>.",
            line=err.line,
            column=err.column,
        ) from err
    parser._expect("IS", "Expected 'is' after state path")
    value = _parse_action_availability_value(parser)
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Action availability requires a quoted text, number, or boolean value.",
            line=extra.line,
            column=extra.column,
        )
    return ast.ActionAvailabilityRule(path=path, value=value, line=only_tok.line, column=only_tok.column)


def _parse_action_availability_rule_block(parser, *, allow_pattern_params: bool = False) -> ast.ActionAvailabilityRule | None:
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
    rule: ast.ActionAvailabilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if rule is not None:
            tok = parser._current()
            raise Namel3ssError(
                "Action availability blocks may only declare one only-when rule.",
                line=tok.line,
                column=tok.column,
            )
        if not _is_visibility_rule_start(parser):
            tok = parser._current()
            raise Namel3ssError(
                "Action availability blocks may only declare an only-when rule.",
                line=tok.line,
                column=tok.column,
            )
        rule = _parse_action_availability_rule_line(parser, allow_pattern_params=allow_pattern_params)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of action availability block")
    if rule is None:
        tok = parser._current()
        raise Namel3ssError("Action availability block has no rule", line=tok.line, column=tok.column)
    return rule


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


def _parse_action_availability_value(parser) -> ast.Literal:
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
    raise Namel3ssError(
        "Action availability requires a quoted text, number, or boolean value.",
        line=tok.line,
        column=tok.column,
    )


def _parse_visibility_rule_block(
    parser,
    *,
    allow_pattern_params: bool = False,
) -> ast.VisibilityRule | ast.VisibilityExpressionRule | None:
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
    rule: ast.VisibilityRule | ast.VisibilityExpressionRule | None = None
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
    visibility: ast.Expression | ast.PatternParamRef | None,
    visibility_rule: ast.VisibilityRule | ast.VisibilityExpressionRule | None,
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


__all__ = [
    "_match_ident_value",
    "_reject_list_transforms",
    "_parse_visibility_clause",
    "_is_show_when_clause_start",
    "_parse_show_when_clause",
    "_parse_debug_only_clause",
    "_parse_debug_only_line",
    "_is_debug_only_start",
    "_is_diagnostics_start",
    "_parse_diagnostics_line",
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
    "_parse_action_availability_rule_line",
    "_parse_action_availability_rule_block",
    "_validate_visibility_combo",
    "_is_param_ref",
    "_parse_param_ref",
    "_parse_style_hooks_block",
    "_parse_variant_line",
]
