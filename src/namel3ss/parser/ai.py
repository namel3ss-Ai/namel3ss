from __future__ import annotations

from namel3ss.ast import nodes as ast_nodes
from namel3ss.errors.base import Namel3ssError


def parse_ai_decl(parser) -> ast_nodes.AIDecl:
    ai_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected AI name string")
    parser._expect("COLON", "Expected ':' after AI name")
    parser._expect("NEWLINE", "Expected newline after AI header")
    parser._expect("INDENT", "Expected indented AI body")
    model = None
    provider = None
    system_prompt = None
    exposed_tools: list[str] = []
    memory = ast_nodes.AIMemory(line=ai_tok.line, column=ai_tok.column)
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._current()
        if key_tok.type == "MODEL":
            parser._advance()
            parser._expect("IS", "Expected 'is' after model")
            value_tok = parser._expect("STRING", "Expected model string")
            model = value_tok.value
        elif key_tok.type == "PROVIDER":
            parser._advance()
            parser._expect("IS", "Expected 'is' after provider")
            value_tok = parser._expect("STRING", "Expected provider string")
            provider = value_tok.value
        elif key_tok.type == "SYSTEM_PROMPT":
            parser._advance()
            parser._expect("IS", "Expected 'is' after system_prompt")
            value_tok = parser._expect("STRING", "Expected system_prompt string")
            system_prompt = value_tok.value
        elif key_tok.type == "TOOLS":
            parser._advance()
            parser._expect("COLON", "Expected ':' after tools")
            parser._expect("NEWLINE", "Expected newline after tools:")
            parser._expect("INDENT", "Expected indented tools block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                if parser._match("EXPOSE"):
                    tool_tok = parser._expect("STRING", "Expected tool name string")
                    tool_name = tool_tok.value
                    if tool_name in exposed_tools:
                        raise Namel3ssError(f"Duplicate tool exposure '{tool_name}'", line=tool_tok.line, column=tool_tok.column)
                    exposed_tools.append(tool_name)
                else:
                    raise Namel3ssError("Unknown entry in tools block", line=parser._current().line, column=parser._current().column)
                parser._match("NEWLINE")
            parser._expect("DEDENT", "Expected end of tools block")
        elif key_tok.type == "MEMORY":
            parser._advance()
            parser._expect("COLON", "Expected ':' after memory")
            parser._expect("NEWLINE", "Expected newline after memory:")
            parser._expect("INDENT", "Expected indented memory block")
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                mem_key = parser._current()
                if mem_key.type == "SHORT_TERM":
                    parser._advance()
                    parser._expect("IS", "Expected 'is' after short_term")
                    value_tok = parser._expect("NUMBER", "short_term must be a number literal")
                    if not isinstance(value_tok.value, int) or value_tok.value < 0:
                        raise Namel3ssError("short_term must be a non-negative integer", line=value_tok.line, column=value_tok.column)
                    memory.short_term = value_tok.value
                elif mem_key.type == "SEMANTIC":
                    parser._advance()
                    parser._expect("IS", "Expected 'is' after semantic")
                    bool_tok = parser._expect("BOOLEAN", "semantic must be true/false literal")
                    memory.semantic = bool_tok.value
                elif mem_key.type == "PROFILE":
                    parser._advance()
                    parser._expect("IS", "Expected 'is' after profile")
                    bool_tok = parser._expect("BOOLEAN", "profile must be true/false literal")
                    memory.profile = bool_tok.value
                else:
                    raise Namel3ssError("Unknown memory field", line=mem_key.line, column=mem_key.column)
                parser._match("NEWLINE")
            parser._expect("DEDENT", "Expected end of memory block")
        else:
            raise Namel3ssError("Unknown field in AI declaration", line=key_tok.line, column=key_tok.column)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of AI body")
    if model is None:
        raise Namel3ssError("AI declaration requires a model", line=ai_tok.line, column=ai_tok.column)
    return ast_nodes.AIDecl(
        name=name_tok.value,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        exposed_tools=exposed_tools,
        memory=memory,
        line=ai_tok.line,
        column=ai_tok.column,
    )


def parse_ask_stmt(parser) -> ast_nodes.AskAIStmt:
    ask_tok = parser._advance()
    parser._expect("AI", "Expected 'ai' after 'ask'")
    name_tok = parser._expect("STRING", "Expected AI name string")
    parser._expect("WITH", "Expected 'with' in ask ai statement")
    parser._expect("INPUT", "Expected 'input' in ask ai statement")
    parser._expect("COLON", "Expected ':' after input")
    input_expr = parser._parse_expression()
    parser._expect("AS", "Expected 'as' to bind AI result")
    target_tok = parser._expect("IDENT", "Expected target identifier after 'as'")
    return ast_nodes.AskAIStmt(ai_name=name_tok.value, input_expr=input_expr, target=target_tok.value, line=ask_tok.line, column=ask_tok.column)
