from __future__ import annotations

from namel3ss.ast import nodes as ast_nodes
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.stmt.ai_input import parse_ai_input_clause


def parse_ask_stmt(parser) -> ast_nodes.AskAIStmt:
    ask_tok = parser._advance()
    parser._expect("AI", "Expected 'ai' after 'ask'")
    ai_name = parse_reference_name(parser, context="AI profile")
    parser._expect("WITH", "Expected 'with' in ask ai statement")
    input_expr, input_mode = parse_ai_input_clause(parser, context="ask ai statement")
    parser._expect("AS", "Expected 'as' to bind AI result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast_nodes.AskAIStmt(
        ai_name=ai_name,
        input_expr=input_expr,
        target=target_tok.value,
        input_mode=input_mode,
        line=ask_tok.line,
        column=ask_tok.column,
    )


__all__ = ["parse_ask_stmt"]
