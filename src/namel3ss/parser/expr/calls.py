from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.decl.tool import _old_tool_syntax_message
from namel3ss.parser.expr.collections import (
    looks_like_list_expression,
    looks_like_list_reduce_expr,
    looks_like_list_transform_expr,
    looks_like_map_expression,
)


def parse_tool_call_expr(parser) -> ast.ToolCallExpr:
    name, line, column = _read_phrase_until(parser, stop_type="COLON", context="tool name")
    parser._expect("COLON", "Expected ':' after tool name")
    parser._expect("NEWLINE", "Expected newline after tool call")
    if not parser._match("INDENT"):
        return ast.ToolCallExpr(tool_name=name, arguments=[], line=line, column=column)
    arguments: List[ast.ToolCallArg] = []
    seen = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        arg_name, arg_line, arg_column = _read_phrase_until(parser, stop_type="IS", context="tool field name")
        parser._expect("IS", "Expected 'is' after tool field name")
        value_expr = parser._parse_expression()
        if arg_name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate tool field '{arg_name}'.",
                    why="Tool call fields must be unique.",
                    fix="Remove or rename the duplicate field.",
                    example='let result is summarize a csv file:\n  file path is "sales.csv"',
                ),
                line=arg_line,
                column=arg_column,
            )
        seen.add(arg_name)
        arguments.append(ast.ToolCallArg(name=arg_name, value=value_expr, line=arg_line, column=arg_column))
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of tool call")
    while parser._match("NEWLINE"):
        pass
    return ast.ToolCallExpr(tool_name=name, arguments=arguments, line=line, column=column)


def looks_like_tool_call(parser) -> bool:
    if parser._current().type in {"ASK", "CALL"}:
        return False
    tok = parser._current()
    if tok.type == "IDENT" and looks_like_list_reduce_expr(parser):
        return False
    if tok.type == "IDENT" and looks_like_list_transform_expr(parser):
        return False
    if tok.type == "IDENT" and tok.value == "list" and looks_like_list_expression(parser):
        return False
    if tok.type == "IDENT" and tok.value == "map" and looks_like_map_expression(parser):
        return False
    pos = parser.position
    while pos < len(parser.tokens):
        tok = parser.tokens[pos]
        if tok.type == "COLON":
            return True
        if tok.type in {"NEWLINE", "EOF", "DEDENT"}:
            return False
        pos += 1
    return False


def parse_old_tool_call(parser):
    tok = parser._current()
    raise Namel3ssError(_old_tool_syntax_message(), line=tok.line, column=tok.column)


def parse_call_function_expr(parser) -> ast.CallFunctionExpr:
    call_tok = parser._advance()
    if not _match_word(parser, "function"):
        raise Namel3ssError(_old_tool_syntax_message(), line=call_tok.line, column=call_tok.column)
    name_tok = parser._expect("STRING", "Expected function name string")
    parser._expect("COLON", "Expected ':' after function name")
    parser._expect("NEWLINE", "Expected newline after function call")
    if not parser._match("INDENT"):
        return ast.CallFunctionExpr(
            function_name=name_tok.value,
            arguments=[],
            line=call_tok.line,
            column=call_tok.column,
        )
    arguments: List[ast.FunctionCallArg] = []
    seen = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        arg_name, arg_line, arg_column = _read_phrase_until(parser, stop_type="IS", context="function argument")
        parser._expect("IS", "Expected 'is' after argument name")
        value_expr = parser._parse_expression()
        if arg_name in seen:
            raise Namel3ssError(
                f"Duplicate function argument '{arg_name}'",
                line=arg_line,
                column=arg_column,
            )
        seen.add(arg_name)
        arguments.append(
            ast.FunctionCallArg(
                name=arg_name,
                value=value_expr,
                line=arg_line,
                column=arg_column,
            )
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of function call")
    while parser._match("NEWLINE"):
        pass
    return ast.CallFunctionExpr(
        function_name=name_tok.value,
        arguments=arguments,
        line=call_tok.line,
        column=call_tok.column,
    )


def parse_ask_expression(parser):
    tok = parser._current()
    raise Namel3ssError(
        'AI calls are statements. Use: ask ai "name" with input: <expr> as <target>.',
        line=tok.line,
        column=tok.column,
    )


def _read_phrase_until(parser, *, stop_type: str, context: str) -> tuple[str, int, int]:
    tokens = []
    while True:
        tok = parser._current()
        if tok.type == stop_type:
            break
        if tok.type in {"NEWLINE", "INDENT", "DEDENT"}:
            raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
        if stop_type != "COLON" and tok.type == "COLON":
            raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
        if tok.type in {"COMMA", "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "PLUS", "MINUS", "STAR", "POWER", "SLASH"}:
            raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
        tokens.append(tok)
        parser._advance()
    if not tokens:
        tok = parser._current()
        raise Namel3ssError(f"Expected {context}", line=tok.line, column=tok.column)
    return _phrase_text(tokens), tokens[0].line, tokens[0].column


def _phrase_text(tokens) -> str:
    parts: List[str] = []
    for tok in tokens:
        if tok.type == "DOT":
            if parts:
                parts[-1] = f"{parts[-1]}."
            else:
                parts.append(".")
            continue
        value = tok.value
        if isinstance(value, bool):
            text = "true" if value else "false"
        elif value is None:
            text = ""
        else:
            text = str(value)
        if not text:
            continue
        if parts and parts[-1].endswith("."):
            parts[-1] = f"{parts[-1]}{text}"
        else:
            parts.append(text)
    return " ".join(parts).strip()


def _match_word(parser, value: str) -> bool:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != value:
        return False
    parser._advance()
    return True


__all__ = [
    "looks_like_tool_call",
    "parse_ask_expression",
    "parse_call_function_expr",
    "parse_old_tool_call",
    "parse_tool_call_expr",
]
