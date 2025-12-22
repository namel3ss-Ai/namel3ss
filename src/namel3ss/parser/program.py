from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.agent import parse_agent_decl
from namel3ss.parser.ai import parse_ai_decl
from namel3ss.parser.app import parse_app
from namel3ss.parser.flow import parse_flow
from namel3ss.parser.pages import parse_page
from namel3ss.parser.records import parse_record
from namel3ss.parser.tool import parse_tool


def parse_program(parser) -> ast.Program:
    app_theme = "system"
    app_line = None
    app_column = None
    theme_tokens = {}
    records: List[ast.RecordDecl] = []
    flows: List[ast.Flow] = []
    pages: List[ast.PageDecl] = []
    ais: List[ast.AIDecl] = []
    tools: List[ast.ToolDecl] = []
    agents: List[ast.AgentDecl] = []
    theme_preference = {"allow_override": (False, None, None), "persist": ("none", None, None)}
    while parser._current().type != "EOF":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type == "APP":
            app_theme, app_line, app_column, theme_tokens, theme_preference = parse_app(parser)
            continue
        if parser._current().type == "TOOL":
            tools.append(parse_tool(parser))
            continue
        if parser._current().type == "AGENT":
            agents.append(parse_agent_decl(parser))
            continue
        if parser._current().type == "AI":
            ais.append(parse_ai_decl(parser))
            continue
        if parser._current().type == "RECORD":
            records.append(parse_record(parser))
            continue
        if parser._current().type == "FLOW":
            flows.append(parse_flow(parser))
            continue
        if parser._current().type == "PAGE":
            pages.append(parse_page(parser))
            continue
        tok = parser._current()
        raise Namel3ssError("Unexpected top-level token", line=tok.line, column=tok.column)
    return ast.Program(
        app_theme=app_theme,
        app_theme_line=app_line,
        app_theme_column=app_column,
        theme_tokens=theme_tokens,
        theme_preference=theme_preference,
        records=records,
        flows=flows,
        pages=pages,
        ais=ais,
        tools=tools,
        agents=agents,
        line=None,
        column=None,
    )
