from __future__ import annotations

from namel3ss.ast import nodes as ast_nodes
from namel3ss.parser.core.helpers import parse_reference_name


def parse_ask_stmt(parser) -> ast_nodes.AskAIStmt:
    ask_tok = parser._advance()
    parser._expect("AI", "Expected 'ai' after 'ask'")
    ai_name = parse_reference_name(parser, context="AI profile")
    parser._expect("WITH", "Expected 'with' in ask ai statement")
    parser._expect("INPUT", "Expected 'input' in ask ai statement")
    parser._expect("COLON", "Expected ':' after input")
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind AI result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast_nodes.AskAIStmt(
        ai_name=ai_name,
        input_expr=input_expr,
        target=target_tok.value,
        line=ask_tok.line,
        column=ask_tok.column,
    )


__all__ = ["parse_ask_stmt"]
