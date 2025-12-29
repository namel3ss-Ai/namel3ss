from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.agent import parse_agent_decl
from namel3ss.parser.ai import parse_ai_decl
from namel3ss.parser.app import parse_app
from namel3ss.parser.flow import parse_flow
from namel3ss.parser.pages import parse_page
from namel3ss.parser.records import parse_record
from namel3ss.parser.modules import parse_capsule_decl, parse_use_decl
from namel3ss.parser.identity import parse_identity
from namel3ss.parser.tool import parse_tool


def parse_program(parser) -> ast.Program:
    spec_version: str | None = None
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
    uses: List[ast.UseDecl] = []
    capsule: ast.CapsuleDecl | None = None
    identity: ast.IdentityDecl | None = None
    theme_preference = {"allow_override": (False, None, None), "persist": ("none", None, None)}
    while parser._current().type != "EOF":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "SPEC":
            if spec_version is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Spec is declared more than once.",
                        why="The spec declaration must appear only once at the program root.",
                        fix="Keep a single spec declaration.",
                        example='spec is \"1.0\"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            parser._advance()
            parser._expect("IS", "Expected 'is' after spec.")
            value = parser._expect("STRING", "Expected a quoted spec version.").value
            spec_version = str(value or "").strip()
            continue
        if tok.type == "IDENT" and tok.value == "use":
            uses.append(parse_use_decl(parser))
            continue
        if tok.type == "IDENT" and tok.value == "capsule":
            if not parser.allow_capsule:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Capsule declaration found in a non-module file.",
                        why="Capsules are only valid in modules/<name>/capsule.ai.",
                        fix="Move the capsule declaration into a module capsule.ai file.",
                        example='modules/inventory/capsule.ai',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            if capsule is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Capsule file declares more than one capsule.",
                        why="Each module has a single capsule contract.",
                        fix="Keep only one capsule declaration per file.",
                        example='capsule "inventory":',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            capsule = parse_capsule_decl(parser)
            continue
        if tok.type == "IDENT" and tok.value == "identity":
            if parser.allow_capsule:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Identity declarations are not allowed in capsule.ai.",
                        why="Identity is defined at the app level.",
                        fix="Move the identity declaration into app.ai.",
                        example='identity "user":',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            if identity is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Multiple identity declarations found.",
                        why="Only one identity block is allowed per app.",
                        fix="Keep a single identity declaration.",
                        example='identity "user":',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            identity = parse_identity(parser)
            continue
        if parser.allow_capsule:
            raise Namel3ssError(
                build_guidance_message(
                    what="Unexpected declaration inside capsule.ai.",
                    why="Capsule files only contain use statements and the capsule exports block.",
                    fix="Move flows/records/pages into other module files.",
                    example='modules/inventory/app.ai',
                ),
                line=tok.line,
                column=tok.column,
            )
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
        raise Namel3ssError("Unexpected top-level token", line=tok.line, column=tok.column)
    if parser.require_spec and not parser.allow_capsule:
        if not spec_version:
            raise Namel3ssError(
                build_guidance_message(
                    what="Spec declaration is missing.",
                    why="Every program must declare the spec version at the root.",
                    fix='Add a spec declaration at the top of the file.',
                    example='spec is \"1.0\"',
                )
            )
    if parser.allow_capsule and capsule is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule file is missing a capsule declaration.",
                why="Every module must declare its capsule and exports.",
                fix='Add `capsule "<name>":` with an exports block.',
                example='capsule "inventory":',
            )
        )
    return ast.Program(
        spec_version=spec_version,
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
        uses=uses,
        capsule=capsule,
        identity=identity,
        line=None,
        column=None,
    )
