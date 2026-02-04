from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.grammar_table import select_top_level_rule
from namel3ss.ui.settings import default_ui_settings_with_meta


def parse_program(parser) -> ast.Program:
    spec_version: str | None = None
    app_theme = default_ui_settings_with_meta()["theme"][0]
    app_line = None
    app_column = None
    theme_tokens = {}
    ui_settings = default_ui_settings_with_meta()
    ui_line = None
    ui_column = None
    ui_active_page_rules = None
    capabilities: list[str] = []
    policy: ast.PolicyDecl | None = None
    packs: list[str] = []
    packs_declared = False
    records: List[ast.RecordDecl] = []
    flows: List[ast.Flow] = []
    jobs: List[ast.JobDecl] = []
    pages: List[ast.PageDecl] = []
    ui_packs: List[ast.UIPackDecl] = []
    ui_patterns: List[ast.UIPatternDecl] = []
    functions: List[ast.FunctionDecl] = []
    contracts: List[ast.ContractDecl] = []
    ais: List[ast.AIDecl] = []
    tools: List[ast.ToolDecl] = []
    agents: List[ast.AgentDecl] = []
    agent_team: ast.AgentTeamDecl | None = None
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
        if rule.name == "contract":
            if parser.allow_capsule:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Contract declarations are not allowed in capsule.ai.",
                        why="Capsule files only contain use statements and the capsule exports block.",
                        fix="Move contract declarations into app.ai.",
                        example='contract flow "demo":',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            contracts.append(rule.parse(parser))
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
        if rule.name == "policy":
            if policy is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Policy is already declared.",
                        why="The policy block is global and must appear only once.",
                        fix="Remove duplicate policy blocks and keep a single block in app.ai.",
                        example="policy\n  allow ingestion.run",
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            policy = rule.parse(parser)
            continue
        if rule.name == "capabilities":
            if capabilities:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Capabilities are already declared.",
                        why="The capabilities block is global and must appear only once.",
                        fix="Remove duplicate capabilities blocks and keep a single block in app.ai.",
                        example="capabilities:\n  http\n  jobs\n  files",
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            capabilities = rule.parse(parser)
            continue
        if rule.name == "packs":
            if packs:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Packs are already declared.",
                        why="The packs block is global and must appear only once.",
                        fix="Remove duplicate packs blocks and keep a single block in app.ai.",
                        example='packs:\\n  "builtin.text"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            packs = rule.parse(parser)
            packs_declared = True
            continue
        if rule.name == "foreign":
            tools.append(rule.parse(parser))
            continue
        if rule.name == "tool":
            tools.append(rule.parse(parser))
            continue
        if rule.name == "agent":
            agents.append(rule.parse(parser))
            continue
        if rule.name == "agent_team":
            if agent_team is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Team of agents is declared more than once.",
                        why="Only one team of agents block is allowed.",
                        fix="Keep a single team of agents block in the app.",
                        example='team of agents\n  \"planner\"\n  \"reviewer\"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            agent_team = rule.parse(parser)
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
        if rule.name == "job":
            jobs.append(rule.parse(parser))
            continue
        if rule.name == "page":
            pages.append(rule.parse(parser))
            continue
        if rule.name == "ui_pack":
            ui_packs.append(rule.parse(parser))
            continue
        if rule.name == "ui_pattern":
            ui_patterns.append(rule.parse(parser))
            continue
        if rule.name == "ui":
            if ui_line is not None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="UI is already declared.",
                        why="The ui block is global and must appear only once.",
                        fix="Remove duplicate ui blocks and keep a single ui block in app.ai.",
                        example='ui:\n  theme is "light"\n  accent color is "blue"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            ui_settings, ui_active_page_rules, ui_line, ui_column = rule.parse(parser)
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
    if ui_line is None:
        ui_settings["theme"] = (app_theme, app_line, app_column)
    program = ast.Program(
        spec_version=spec_version,
        app_theme=app_theme,
        app_theme_line=app_line,
        app_theme_column=app_column,
        theme_tokens=theme_tokens,
        theme_preference=theme_preference,
        ui_settings=ui_settings,
        ui_line=ui_line,
        ui_column=ui_column,
        ui_active_page_rules=ui_active_page_rules,
        capabilities=capabilities,
        records=records,
        functions=functions,
        contracts=contracts,
        flows=flows,
        jobs=jobs,
        pages=pages,
        ui_packs=ui_packs,
        ui_patterns=ui_patterns,
        ais=ais,
        tools=tools,
        agents=agents,
        agent_team=agent_team,
        uses=uses,
        capsule=capsule,
        identity=identity,
        policy=policy,
        line=None,
        column=None,
    )
    setattr(program, "pack_allowlist", list(packs) if packs_declared else None)
    return program


__all__ = ["parse_program"]
