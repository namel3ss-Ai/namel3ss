from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name


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
            ai_name = parse_reference_name(parser, context="AI profile")
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


__all__ = ["parse_agent_decl"]
