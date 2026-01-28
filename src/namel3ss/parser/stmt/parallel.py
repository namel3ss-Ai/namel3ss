from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_parallel(parser) -> ast.ParallelBlock:
    parallel_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after parallel")
    parser._expect("NEWLINE", "Expected newline after parallel")
    parser._expect("INDENT", "Expected indented parallel block")
    tasks: list[ast.ParallelTask] = []
    merge: ast.ParallelMergePolicy | None = None
    saw_merge = False
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "merge":
            if saw_merge:
                raise Namel3ssError("Parallel merge block is declared more than once", line=tok.line, column=tok.column)
            merge = _parse_merge_block(parser, tok)
            saw_merge = True
            continue
        run_tok = parser._expect("RUN", "Expected 'run' in parallel block")
        if saw_merge:
            raise Namel3ssError("Parallel tasks must come before merge block", line=run_tok.line, column=run_tok.column)
        name_tok = parser._expect("STRING", "Expected task name string after run")
        parser._expect("COLON", "Expected ':' after task name")
        body = parser._parse_block()
        tasks.append(
            ast.ParallelTask(
                name=name_tok.value,
                body=body,
                line=run_tok.line,
                column=run_tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of parallel block")
    if not tasks:
        raise Namel3ssError("Parallel block requires at least one task", line=parallel_tok.line, column=parallel_tok.column)
    return ast.ParallelBlock(tasks=tasks, merge=merge, line=parallel_tok.line, column=parallel_tok.column)


def _parse_merge_block(parser, merge_tok) -> ast.ParallelMergePolicy:
    parser._advance()
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
    _validate_merge_policy(policy, fields.get("policy")[0] if "policy" in fields else merge_tok)
    _reject_unknown_fields(fields, {"policy"})
    return ast.ParallelMergePolicy(policy=policy, line=merge_tok.line, column=merge_tok.column)


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


def _literal_value(expr, *, name: str, tok) -> object:
    if isinstance(expr, ast.Literal):
        return expr.value
    raise Namel3ssError(
        f"Merge field '{name}' must be a literal value.",
        line=tok.line,
        column=tok.column,
    )


def _validate_merge_policy(policy: str, policy_tok) -> None:
    allowed = {"conflict", "precedence", "override"}
    if policy not in allowed:
        raise Namel3ssError(
            f"Unknown merge policy '{policy}'.",
            line=policy_tok.line,
            column=policy_tok.column,
        )


__all__ = ["parse_parallel"]
