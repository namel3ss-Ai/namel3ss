from __future__ import annotations

from typing import List, Set

from namel3ss.ast import nodes as ast


def parse_flow(parser) -> ast.Flow:
    flow_tok = parser._expect("FLOW", "Expected 'flow' declaration")
    name_tok = parser._expect("STRING", "Expected flow name string")
    parser._expect("COLON", "Expected ':' after flow name")
    parser._expect("NEWLINE", "Expected newline after flow header")
    parser._expect("INDENT", "Expected indented block for flow body")
    body = parse_statements(parser, until={"DEDENT"})
    parser._expect("DEDENT", "Expected block end")
    while parser._match("NEWLINE"):
        pass
    return ast.Flow(name=name_tok.value, body=body, line=flow_tok.line, column=flow_tok.column)


def parse_statements(parser, until: Set[str]) -> List[ast.Statement]:
    statements: List[ast.Statement] = []
    while parser._current().type not in until:
        if parser._match("NEWLINE"):
            continue
        statements.append(parser._parse_statement())
    return statements


def parse_block(parser) -> List[ast.Statement]:
    parser._expect("NEWLINE", "Expected newline before block")
    parser._expect("INDENT", "Expected indented block")
    stmts = parse_statements(parser, until={"DEDENT"})
    parser._expect("DEDENT", "Expected end of block")
    while parser._match("NEWLINE"):
        pass
    return stmts
