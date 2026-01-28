from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


_ALLOWED_POLICIES = {"first_ok", "all_ok", "collect", "prefer", "strict"}


def parse_orchestration(parser) -> ast.OrchestrationBlock:
    orchestration_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after orchestration")
    parser._expect("NEWLINE", "Expected newline after orchestration")
    parser._expect("INDENT", "Expected indented orchestration block")
    branches: list[ast.OrchestrationBranch] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        branch_tok = _expect_ident_value(parser, "branch", "Expected 'branch' in orchestration block")
        name_tok = parser._expect("STRING", "Expected branch name string after branch")
        if name_tok.value in seen:
            raise Namel3ssError(
                f'Branch "{name_tok.value}" is declared more than once.',
                line=name_tok.line,
                column=name_tok.column,
            )
        seen.add(name_tok.value)
        parser._expect("COLON", "Expected ':' after branch name")
        parser._expect("NEWLINE", "Expected newline after branch header")
        parser._expect("INDENT", "Expected indented branch block")
        call_expr = _parse_branch_expression(parser, name_tok)
        parser._expect("DEDENT", "Expected end of branch block")
        branches.append(
            ast.OrchestrationBranch(
                name=name_tok.value,
                call_expr=call_expr,
                line=branch_tok.line,
                column=branch_tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of orchestration block")
    if not branches:
        raise Namel3ssError(
            "Orchestration block requires at least one branch",
            line=orchestration_tok.line,
            column=orchestration_tok.column,
        )
    merge_tok = _match_ident_value(parser, "merge")
    if merge_tok is None:
        raise Namel3ssError(
            "Orchestration merge block is required",
            line=orchestration_tok.line,
            column=orchestration_tok.column,
        )
    merge = _parse_merge_block(parser, merge_tok, branch_names=[branch.name for branch in branches])
    parser._expect("AS", "Expected 'as' after merge block")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast.OrchestrationBlock(
        branches=branches,
        merge=merge,
        target=target_tok.value,
        line=orchestration_tok.line,
        column=orchestration_tok.column,
    )


def _parse_branch_expression(parser, name_tok) -> ast.Expression:
    while parser._match("NEWLINE"):
        pass
    expr = parser._parse_expression()
    if not isinstance(expr, (ast.CallFlowExpr, ast.CallPipelineExpr)):
        raise Namel3ssError(
            "Orchestration branches must call a flow or pipeline.",
            line=expr.line if expr.line is not None else name_tok.line,
            column=expr.column if expr.column is not None else name_tok.column,
        )
    while parser._match("NEWLINE"):
        pass
    if parser._current().type != "DEDENT":
        tok = parser._current()
        raise Namel3ssError(
            "Orchestration branches must contain a single call.",
            line=tok.line,
            column=tok.column,
        )
    return expr


def _parse_merge_block(parser, merge_tok, *, branch_names: list[str]) -> ast.OrchestrationMergePolicy:
    parser._expect("COLON", "Expected ':' after merge")
    parser._expect("NEWLINE", "Expected newline after merge")
    parser._expect("INDENT", "Expected indented merge block")
    fields: dict[str, tuple[object, object]] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        name_tok = parser._expect("IDENT", "Expected merge field name")
        field_name = name_tok.value
        if field_name in fields:
            raise Namel3ssError(
                f"Merge field '{field_name}' is declared more than once.",
                line=name_tok.line,
                column=name_tok.column,
            )
        parser._expect("IS", "Expected 'is' after merge field")
        value_expr = parser._parse_expression()
        fields[field_name] = (name_tok, value_expr)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of merge block")
    policy = _require_literal_string(fields, "policy", merge_tok)
    precedence = _optional_string_list(fields, "precedence")
    _validate_merge_policy(policy, fields.get("policy")[0] if "policy" in fields else merge_tok, precedence=precedence)
    _reject_unknown_fields(fields, {"policy", "precedence"})
    _validate_precedence(policy, precedence, branch_names, merge_tok)
    return ast.OrchestrationMergePolicy(
        policy=policy,
        precedence=precedence,
        line=merge_tok.line,
        column=merge_tok.column,
    )


def _validate_precedence(
    policy: str,
    precedence: list[str] | None,
    branch_names: list[str],
    merge_tok,
) -> None:
    if policy != "prefer":
        if precedence:
            raise Namel3ssError(
                "Merge field 'precedence' is only allowed with policy 'prefer'.",
                line=merge_tok.line,
                column=merge_tok.column,
            )
        return
    if not precedence:
        raise Namel3ssError(
            "Merge policy 'prefer' requires precedence.",
            line=merge_tok.line,
            column=merge_tok.column,
        )
    seen: set[str] = set()
    for name in precedence:
        if name in seen:
            raise Namel3ssError(
                f"Merge precedence '{name}' is duplicated.",
                line=merge_tok.line,
                column=merge_tok.column,
            )
        seen.add(name)
        if name not in branch_names:
            raise Namel3ssError(
                f"Merge precedence '{name}' does not match a branch.",
                line=merge_tok.line,
                column=merge_tok.column,
            )


def _match_ident_value(parser, value: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    return None


def _expect_ident_value(parser, value: str, message: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        return parser._advance()
    raise Namel3ssError(message, line=tok.line, column=tok.column)


def _reject_unknown_fields(fields: dict[str, tuple[object, object]], allowed: set[str]) -> None:
    for name, (tok, _expr) in fields.items():
        if name not in allowed:
            raise Namel3ssError(
                f"Unknown merge field '{name}'.",
                line=tok.line,
                column=tok.column,
            )


def _require_literal_string(fields: dict[str, tuple[object, object]], name: str, fallback_tok) -> str:
    if name not in fields:
        raise Namel3ssError(
            f"Merge field '{name}' is required.",
            line=fallback_tok.line,
            column=fallback_tok.column,
        )
    tok, expr = fields[name]
    value = _literal_value(expr, name=name, tok=tok)
    if not isinstance(value, str) or not value:
        raise Namel3ssError(
            f"Merge field '{name}' must be a non-empty string.",
            line=tok.line,
            column=tok.column,
        )
    return value


def _optional_string_list(fields: dict[str, tuple[object, object]], name: str) -> list[str] | None:
    if name not in fields:
        return None
    tok, expr = fields[name]
    if isinstance(expr, ast.Literal):
        value = expr.value
        if isinstance(value, str) and value:
            return [value]
        raise Namel3ssError(
            f"Merge field '{name}' must be a list of strings.",
            line=tok.line,
            column=tok.column,
        )
    if not isinstance(expr, ast.ListExpr):
        raise Namel3ssError(
            f"Merge field '{name}' must be a list of strings.",
            line=tok.line,
            column=tok.column,
        )
    values: list[str] = []
    for item in expr.items:
        if not isinstance(item, ast.Literal) or not isinstance(item.value, str) or not item.value:
            raise Namel3ssError(
                f"Merge field '{name}' must contain only strings.",
                line=tok.line,
                column=tok.column,
            )
        values.append(item.value)
    return values


def _literal_value(expr, *, name: str, tok) -> object:
    if isinstance(expr, ast.Literal):
        return expr.value
    raise Namel3ssError(
        f"Merge field '{name}' must be a literal value.",
        line=tok.line,
        column=tok.column,
    )


def _validate_merge_policy(policy: str, policy_tok, *, precedence: list[str] | None) -> None:
    if policy not in _ALLOWED_POLICIES:
        raise Namel3ssError(
            f"Unknown merge policy '{policy}'.",
            line=policy_tok.line,
            column=policy_tok.column,
        )
    if policy != "prefer" and precedence:
        raise Namel3ssError(
            "Merge field 'precedence' is only allowed with policy 'prefer'.",
            line=policy_tok.line,
            column=policy_tok.column,
        )


__all__ = ["parse_orchestration"]
