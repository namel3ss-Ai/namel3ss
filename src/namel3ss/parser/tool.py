from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_tool(parser) -> ast.ToolDecl:
    tool_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected tool name string")
    parser._expect("COLON", "Expected ':' after tool name")
    parser._expect("NEWLINE", "Expected newline after tool header")
    parser._expect("INDENT", "Expected indented tool body")
    kind = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        key_tok = parser._current()
        if key_tok.type == "KIND":
            parser._advance()
            parser._expect("IS", "Expected 'is' after kind")
            kind_tok = parser._expect("STRING", "Expected kind string")
            kind = kind_tok.value
        else:
            raise Namel3ssError("Unknown field in tool declaration", line=key_tok.line, column=key_tok.column)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of tool body")
    if kind is None:
        raise Namel3ssError("Tool declaration requires a kind", line=tool_tok.line, column=tool_tok.column)
    return ast.ToolDecl(name=name_tok.value, kind=kind, line=tool_tok.line, column=tool_tok.column)
