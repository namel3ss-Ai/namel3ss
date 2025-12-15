from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.agent import parse_agent_decl, parse_run_agent_stmt, parse_run_agents_parallel
from namel3ss.parser.ai import parse_ai_decl, parse_ask_stmt
from namel3ss.parser.tool import parse_tool


def parse_statement(parser) -> ast.Statement:
    tok = parser._current()
    if tok.type == "LET":
        return parse_let(parser)
    if tok.type == "SET":
        return parse_set(parser)
    if tok.type == "IF":
        return parse_if(parser)
    if tok.type == "RETURN":
        return parse_return(parser)
    if tok.type == "ASK":
        return parse_ask_stmt(parser)
    if tok.type == "RUN":
        next_type = parser.tokens[parser.position + 1].type
        if next_type == "AGENT":
            return parse_run_agent_stmt(parser)
        if next_type == "AGENTS":
            return parse_run_agents_parallel(parser)
        raise Namel3ssError("Expected 'agent' or 'agents' after run", line=tok.line, column=tok.column)
    if tok.type == "REPEAT":
        return parse_repeat(parser)
    if tok.type == "FOR":
        return parse_for_each(parser)
    if tok.type == "MATCH":
        return parse_match(parser)
    if tok.type == "TRY":
        return parse_try(parser)
    if tok.type == "SAVE":
        return parse_save(parser)
    if tok.type == "FIND":
        return parse_find(parser)
    raise Namel3ssError(f"Unexpected token '{tok.type}' in statement", line=tok.line, column=tok.column)


def parse_let(parser) -> ast.Let:
    let_tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected identifier after 'let'")
    parser._expect("IS", "Expected 'is' in declaration")
    expr = parser._parse_expression()
    constant = False
    if parser._match("CONSTANT"):
        constant = True
    return ast.Let(name=name_tok.value, expression=expr, constant=constant, line=let_tok.line, column=let_tok.column)


def parse_set(parser) -> ast.Set:
    set_tok = parser._advance()
    target = parse_target(parser)
    parser._expect("IS", "Expected 'is' in assignment")
    expr = parser._parse_expression()
    return ast.Set(target=target, expression=expr, line=set_tok.line, column=set_tok.column)


def parse_if(parser) -> ast.If:
    if_tok = parser._advance()
    condition = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after condition")
    parser._expect("NEWLINE", "Expected newline after condition")
    parser._expect("INDENT", "Expected indented block for if body")
    then_body = parser._parse_statements(until={"DEDENT"})
    parser._expect("DEDENT", "Expected block end")
    else_body: List[ast.Statement] = []
    while parser._match("NEWLINE"):
        pass
    if parser._match("ELSE"):
        parser._expect("COLON", "Expected ':' after else")
        parser._expect("NEWLINE", "Expected newline after else")
        parser._expect("INDENT", "Expected indented block for else body")
        else_body = parser._parse_statements(until={"DEDENT"})
        parser._expect("DEDENT", "Expected block end")
        while parser._match("NEWLINE"):
            pass
    return ast.If(
        condition=condition,
        then_body=then_body,
        else_body=else_body,
        line=if_tok.line,
        column=if_tok.column,
    )


def parse_return(parser) -> ast.Return:
    ret_tok = parser._advance()
    expr = parser._parse_expression()
    return ast.Return(expression=expr, line=ret_tok.line, column=ret_tok.column)


def parse_repeat(parser) -> ast.Repeat:
    rep_tok = parser._advance()
    parser._expect("UP", "Expected 'up' in repeat statement")
    parser._expect("TO", "Expected 'to' in repeat statement")
    count_expr = parser._parse_expression()
    parser._expect("TIMES", "Expected 'times' after repeat count")
    parser._expect("COLON", "Expected ':' after repeat header")
    body = parser._parse_block()
    return ast.Repeat(count=count_expr, body=body, line=rep_tok.line, column=rep_tok.column)


def parse_for_each(parser) -> ast.ForEach:
    for_tok = parser._advance()
    parser._expect("EACH", "Expected 'each' after 'for'")
    name_tok = parser._expect("IDENT", "Expected loop variable name")
    parser._expect("IN", "Expected 'in' in for-each loop")
    iterable = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after for-each header")
    body = parser._parse_block()
    return ast.ForEach(name=name_tok.value, iterable=iterable, body=body, line=for_tok.line, column=for_tok.column)


def parse_match(parser) -> ast.Match:
    match_tok = parser._advance()
    expr = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after match expression")
    parser._expect("NEWLINE", "Expected newline after match header")
    parser._expect("INDENT", "Expected indented match body")
    parser._expect("WITH", "Expected 'with' inside match")
    parser._expect("COLON", "Expected ':' after 'with'")
    parser._expect("NEWLINE", "Expected newline after 'with:'")
    parser._expect("INDENT", "Expected indented match cases")
    cases: List[ast.MatchCase] = []
    otherwise_body: List[ast.Statement] | None = None
    while parser._current().type not in {"DEDENT"}:
        if parser._match("WHEN"):
            pattern_expr = parser._parse_expression()
            parser._validate_match_pattern(pattern_expr)
            parser._expect("COLON", "Expected ':' after when pattern")
            case_body = parser._parse_block()
            if otherwise_body is not None:
                raise Namel3ssError("Unreachable case after otherwise", line=pattern_expr.line, column=pattern_expr.column)
            cases.append(ast.MatchCase(pattern=pattern_expr, body=case_body, line=pattern_expr.line, column=pattern_expr.column))
            continue
        if parser._match("OTHERWISE"):
            if otherwise_body is not None:
                tok = parser.tokens[parser.position - 1]
                raise Namel3ssError("Duplicate otherwise in match", line=tok.line, column=tok.column)
            parser._expect("COLON", "Expected ':' after otherwise")
            otherwise_body = parser._parse_block()
            continue
        tok = parser._current()
        raise Namel3ssError("Expected 'when' or 'otherwise' in match", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of match cases")
    parser._expect("DEDENT", "Expected end of match block")
    while parser._match("NEWLINE"):
        pass
    if not cases and otherwise_body is None:
        raise Namel3ssError("Match must have at least one case", line=match_tok.line, column=match_tok.column)
    return ast.Match(expression=expr, cases=cases, otherwise=otherwise_body, line=match_tok.line, column=match_tok.column)


def parse_try(parser) -> ast.TryCatch:
    try_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after try")
    try_body = parser._parse_block()
    if not parser._match("WITH"):
        tok = parser._current()
        raise Namel3ssError("Expected 'with' introducing catch", line=tok.line, column=tok.column)
    parser._expect("CATCH", "Expected 'catch' after 'with'")
    var_tok = parser._expect("IDENT", "Expected catch variable name")
    parser._expect("COLON", "Expected ':' after catch clause")
    catch_body = parser._parse_block()
    return ast.TryCatch(try_body=try_body, catch_var=var_tok.value, catch_body=catch_body, line=try_tok.line, column=try_tok.column)


def parse_save(parser) -> ast.Save:
    tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected record name after 'save'")
    return ast.Save(record_name=name_tok.value, line=tok.line, column=tok.column)


def parse_find(parser) -> ast.Find:
    tok = parser._advance()
    name_tok = parser._expect("IDENT", "Expected record name after 'find'")
    parser._expect("WHERE", "Expected 'where' in find statement")
    predicate = parser._parse_expression()
    return ast.Find(record_name=name_tok.value, predicate=predicate, line=tok.line, column=tok.column)


def parse_target(parser) -> ast.Assignable:
    tok = parser._current()
    if tok.type == "STATE":
        return parser._parse_state_path()
    if tok.type == "IDENT":
        name_tok = parser._advance()
        return ast.VarReference(name=name_tok.value, line=name_tok.line, column=name_tok.column)
    raise Namel3ssError("Expected assignment target", line=tok.line, column=tok.column)


def validate_match_pattern(parser, pattern: ast.Expression) -> None:
    if isinstance(pattern, (ast.Literal, ast.VarReference, ast.StatePath)):
        return
    raise Namel3ssError("Match patterns must be literal or identifier", line=pattern.line, column=pattern.column)


__all__ = [
    "parse_statement",
    "parse_let",
    "parse_set",
    "parse_if",
    "parse_return",
    "parse_repeat",
    "parse_for_each",
    "parse_match",
    "parse_try",
    "parse_save",
    "parse_find",
    "parse_target",
    "parse_ai_decl",
    "parse_tool",
    "parse_agent_decl",
    "validate_match_pattern",
]
