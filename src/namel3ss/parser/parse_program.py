from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.grammar_table import select_top_level_rule


def parse_program(parser) -> ast.Program:
    spec_version: str | None = None
    app_theme = "system"
    app_line = None
    app_column = None
    theme_tokens = {}
    records: List[ast.RecordDecl] = []
    flows: List[ast.Flow] = []
    pages: List[ast.PageDecl] = []
    ui_packs: List[ast.UIPackDecl] = []
    functions: List[ast.FunctionDecl] = []
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
        rule = select_top_level_rule(parser)
        if rule is None:
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
            raise Namel3ssError("Unexpected top-level token", line=tok.line, column=tok.column)
        if rule.name == "spec":
            if spec_version is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Spec is declared more than once.",
                        why="The spec declaration must appear only once at the program root.",
                        fix="Keep a single spec declaration.",
                        example='spec is "1.0"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            spec_version = rule.parse(parser)
            continue
        if rule.name == "use":
            uses.append(rule.parse(parser))
            continue
        if rule.name == "function":
            if parser.allow_capsule:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Function declarations are not allowed in capsule.ai.",
                        why="Capsule files only contain use statements and the capsule exports block.",
                        fix="Move function declarations into app or module files.",
                        example='modules/inventory/app.ai',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            functions.append(rule.parse(parser))
            continue
        if rule.name == "capsule":
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
            capsule = rule.parse(parser)
            continue
        if rule.name == "identity":
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
            identity = rule.parse(parser)
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
        if rule.name == "app":
            app_theme, app_line, app_column, theme_tokens, theme_preference = rule.parse(parser)
            continue
        if rule.name == "tool":
            tools.append(rule.parse(parser))
            continue
        if rule.name == "agent":
            agents.append(rule.parse(parser))
            continue
        if rule.name == "ai":
            ais.append(rule.parse(parser))
            continue
        if rule.name == "record":
            records.append(rule.parse(parser))
            continue
        if rule.name == "flow":
            flows.append(rule.parse(parser))
            continue
        if rule.name == "page":
            pages.append(rule.parse(parser))
            continue
        if rule.name == "ui_pack":
            ui_packs.append(rule.parse(parser))
            continue
        raise Namel3ssError("Unexpected top-level token", line=tok.line, column=tok.column)
    if parser.require_spec and not parser.allow_capsule:
        if not spec_version:
            raise Namel3ssError(
                build_guidance_message(
                    what="Spec declaration is missing.",
                    why="Every program must declare the spec version at the root.",
                    fix='Add a spec declaration at the top of the file.',
                    example='spec is "1.0"',
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
        functions=functions,
        flows=flows,
        pages=pages,
        ui_packs=ui_packs,
        ais=ais,
        tools=tools,
        agents=agents,
        uses=uses,
        capsule=capsule,
        identity=identity,
        line=None,
        column=None,
    )


__all__ = ["parse_program"]
