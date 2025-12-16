from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_agent_decl(parser) -> ast.AgentDecl:
    agent_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected agent name string")
    parser._expect("COLON", "Expected ':' after agent name")
    parser._expect("NEWLINE", "Expected newline after agent header")
    parser._expect("INDENT", "Expected indented agent body")
    ai_name = None
    system_prompt = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._current()
        if key_tok.type == "AI":
            parser._advance()
            parser._expect("IS", "Expected 'is' after ai")
            ai_tok = parser._expect("STRING", "Expected AI profile name")
            ai_name = ai_tok.value
        elif key_tok.type == "SYSTEM_PROMPT":
            parser._advance()
            parser._expect("IS", "Expected 'is' after system_prompt")
            sp_tok = parser._expect("STRING", "Expected system_prompt string")
            system_prompt = sp_tok.value
        else:
            raise Namel3ssError("Unknown field in agent declaration", line=key_tok.line, column=key_tok.column)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of agent body")
    if ai_name is None:
        raise Namel3ssError("Agent requires an AI profile", line=agent_tok.line, column=agent_tok.column)
    return ast.AgentDecl(name=name_tok.value, ai_name=ai_name, system_prompt=system_prompt, line=agent_tok.line, column=agent_tok.column)


def parse_run_agent_stmt(parser) -> ast.RunAgentStmt:
    run_tok = parser._advance()
    if not parser._match("AGENT"):
        raise Namel3ssError("Expected 'agent' after run", line=run_tok.line, column=run_tok.column)
    name_tok = parser._expect("STRING", "Expected agent name string")
    parser._expect("WITH", "Expected 'with' in run agent")
    parser._expect("INPUT", "Expected 'input' in run agent")
    parser._expect("COLON", "Expected ':' after input")
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind agent result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast.RunAgentStmt(agent_name=name_tok.value, input_expr=input_expr, target=target_tok.value, line=run_tok.line, column=run_tok.column)


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
        name_tok = parser._expect("STRING", "Expected agent name string")
        parser._expect("WITH", "Expected 'with' in agent entry")
        parser._expect("INPUT", "Expected 'input' in agent entry")
        parser._expect("COLON", "Expected ':' after input")
        input_expr = parser._parse_expression()
        entries.append(ast.ParallelAgentEntry(agent_name=name_tok.value, input_expr=input_expr, line=name_tok.line, column=name_tok.column))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of parallel agents block")
    if not entries:
        raise Namel3ssError("Parallel agent block requires at least one entry", line=run_tok.line, column=run_tok.column)
    parser._expect("AS", "Expected 'as' after parallel block")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast.RunAgentsParallelStmt(entries=entries, target=target_tok.value, line=run_tok.line, column=run_tok.column)
