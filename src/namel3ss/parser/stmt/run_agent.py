from __future__ import annotations

from decimal import Decimal

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name


def parse_run_agent_stmt(parser) -> ast.RunAgentStmt:
    run_tok = parser._advance()
    if not parser._match("AGENT"):
        raise Namel3ssError("Expected 'agent' after run", line=run_tok.line, column=run_tok.column)
    name_tok = parser._current()
    agent_name = parse_reference_name(parser, context="agent")
    parser._expect("WITH", "Expected 'with' in run agent")
    parser._expect("INPUT", "Expected 'input' in run agent")
    parser._expect("COLON", "Expected ':' after input")
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind agent result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast.RunAgentStmt(
        agent_name=agent_name,
        input_expr=input_expr,
        target=target_tok.value,
        line=name_tok.line,
        column=name_tok.column,
    )


def parse_run_agents_parallel(parser) -> ast.RunAgentsParallelStmt:
    run_tok = parser._advance()
    if not parser._match("AGENTS"):
        raise Namel3ssError("Expected 'agents' after run", line=run_tok.line, column=run_tok.column)
    parser._expect("IN", "Expected 'in'")
    parser._expect("PARALLEL", "Expected 'parallel'")
    parser._expect("COLON", "Expected ':' after parallel header")
    parser._expect("NEWLINE", "Expected newline after parallel header")
    parser._expect("INDENT", "Expected indented parallel block")
    entries: list[ast.ParallelAgentEntry] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        parser._expect("AGENT", "Expected 'agent' in parallel block")
        name_tok = parser._current()
        agent_name = parse_reference_name(parser, context="agent")
        parser._expect("WITH", "Expected 'with' in agent entry")
        parser._expect("INPUT", "Expected 'input' in agent entry")
        parser._expect("COLON", "Expected ':' after input")
        input_expr = parser._parse_expression()
        entries.append(
            ast.ParallelAgentEntry(
                agent_name=agent_name,
                input_expr=input_expr,
                line=name_tok.line,
                column=name_tok.column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of parallel agents block")
    if not entries:
        raise Namel3ssError("Parallel agent block requires at least one entry", line=run_tok.line, column=run_tok.column)
    merge = None
    merge_tok = _match_ident_value(parser, "merge")
    if merge_tok is not None:
        merge = _parse_merge_block(parser, merge_tok)
    parser._expect("AS", "Expected 'as' after parallel block")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast.RunAgentsParallelStmt(
        entries=entries,
        target=target_tok.value,
        merge=merge,
        line=run_tok.line,
        column=run_tok.column,
    )


def _parse_merge_block(parser, merge_tok) -> ast.AgentMergePolicy:
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
    require_keys = _optional_string_list(fields, "require_keys")
    require_non_empty = _optional_literal_bool(fields, "require_non_empty")
    score_key = _optional_literal_string(fields, "score_key")
    score_rule = _optional_literal_string(fields, "score_rule")
    min_consensus = _optional_literal_int(fields, "min_consensus")
    consensus_key = _optional_literal_string(fields, "consensus_key")
    _validate_merge_policy(
        policy,
        fields.get("policy")[0] if "policy" in fields else merge_tok,
        score_key=score_key,
        score_rule=score_rule,
        min_consensus=min_consensus,
    )
    _reject_unknown_fields(
        fields,
        {
            "policy",
            "require_keys",
            "require_non_empty",
            "score_key",
            "score_rule",
            "min_consensus",
            "consensus_key",
        },
    )
    return ast.AgentMergePolicy(
        policy=policy,
        require_keys=require_keys,
        require_non_empty=require_non_empty,
        score_key=score_key,
        score_rule=score_rule,
        min_consensus=min_consensus,
        consensus_key=consensus_key,
        line=merge_tok.line,
        column=merge_tok.column,
    )


def _match_ident_value(parser, value: str):
    tok = parser._current()
    if tok.type == "IDENT" and tok.value == value:
        parser._advance()
        return tok
    return None


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


def _optional_literal_string(fields: dict[str, tuple[object, object]], name: str) -> str | None:
    if name not in fields:
        return None
    tok, expr = fields[name]
    value = _literal_value(expr, name=name, tok=tok)
    if not isinstance(value, str) or not value:
        raise Namel3ssError(
            f"Merge field '{name}' must be a non-empty string.",
            line=tok.line,
            column=tok.column,
        )
    return value


def _optional_literal_bool(fields: dict[str, tuple[object, object]], name: str) -> bool | None:
    if name not in fields:
        return None
    tok, expr = fields[name]
    value = _literal_value(expr, name=name, tok=tok)
    if not isinstance(value, bool):
        raise Namel3ssError(
            f"Merge field '{name}' must be true or false.",
            line=tok.line,
            column=tok.column,
        )
    return value


def _optional_literal_int(fields: dict[str, tuple[object, object]], name: str) -> int | None:
    if name not in fields:
        return None
    tok, expr = fields[name]
    value = _literal_value(expr, name=name, tok=tok)
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise Namel3ssError(
            f"Merge field '{name}' must be a number.",
            line=tok.line,
            column=tok.column,
        )
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise Namel3ssError(
                f"Merge field '{name}' must be a positive integer.",
                line=tok.line,
                column=tok.column,
            )
        numeric = int(value)
    else:
        numeric = int(value)
        if numeric != value:
            raise Namel3ssError(
                f"Merge field '{name}' must be a positive integer.",
                line=tok.line,
                column=tok.column,
            )
    if numeric <= 0:
        raise Namel3ssError(
            f"Merge field '{name}' must be a positive integer.",
            line=tok.line,
            column=tok.column,
        )
    return int(numeric)


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


def _validate_merge_policy(
    policy: str,
    tok,
    *,
    score_key: str | None,
    score_rule: str | None,
    min_consensus: int | None,
) -> None:
    allowed = {"first_valid", "ranked", "consensus", "all"}
    if policy not in allowed:
        raise Namel3ssError(
            f"Unknown merge policy '{policy}'.",
            line=tok.line,
            column=tok.column,
        )
    if policy == "ranked" and not (score_key or score_rule):
        raise Namel3ssError(
            "Merge policy 'ranked' requires score_key or score_rule.",
            line=tok.line,
            column=tok.column,
        )
    if policy == "ranked" and score_key and score_rule:
        raise Namel3ssError(
            "Merge policy 'ranked' may not set both score_key and score_rule.",
            line=tok.line,
            column=tok.column,
        )
    if policy == "ranked" and score_rule and score_rule not in {"text_length"}:
        raise Namel3ssError(
            f"Merge policy 'ranked' does not support score_rule '{score_rule}'.",
            line=tok.line,
            column=tok.column,
        )
    if policy == "consensus" and not min_consensus:
        raise Namel3ssError(
            "Merge policy 'consensus' requires min_consensus.",
            line=tok.line,
            column=tok.column,
        )


__all__ = ["parse_run_agent_stmt", "parse_run_agents_parallel"]
