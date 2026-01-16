from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_agent_team_decl(parser) -> ast.AgentTeamDecl:
    team_tok = parser._advance()
    of_tok = parser._expect("IDENT", "Expected 'of' after team")
    if of_tok.value != "of":
        raise Namel3ssError("Expected 'of' after team", line=of_tok.line, column=of_tok.column)
    parser._expect("AGENTS", "Expected 'agents' after team of")
    parser._expect("NEWLINE", "Expected newline after team of agents")
    parser._expect("INDENT", "Expected indented team body")
    members: list[ast.AgentTeamMember] = []
    form: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "STRING":
            if form is None:
                form = "list"
            elif form != "list":
                raise Namel3ssError(
                    build_guidance_message(
                        what="Team of agents mixes list and block forms.",
                        why="Use either the list form or the explicit agent block form.",
                        fix="Pick one form and remove the other entries.",
                        example='team of agents\n  "planner"\n  "reviewer"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            name_tok = parser._advance()
            members.append(
                ast.AgentTeamMember(
                    name=name_tok.value,
                    role=None,
                    line=name_tok.line,
                    column=name_tok.column,
                )
            )
            parser._match("NEWLINE")
            continue
        if tok.type == "AGENT":
            if form is None:
                form = "block"
            elif form != "block":
                raise Namel3ssError(
                    build_guidance_message(
                        what="Team of agents mixes block and list forms.",
                        why="Use either the explicit agent blocks or the list form.",
                        fix="Pick one form and remove the other entries.",
                        example='team of agents\n  agent "planner"\n    role is "Plans"',
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            parser._advance()
            name_tok = parser._expect("STRING", "Expected agent name string")
            parser._expect("NEWLINE", "Expected newline after agent name")
            parser._expect("INDENT", "Expected indented agent block")
            role = None
            while parser._current().type != "DEDENT":
                if parser._match("NEWLINE"):
                    continue
                key_tok = parser._current()
                if key_tok.type == "IDENT" and key_tok.value == "role":
                    if role is not None:
                        raise Namel3ssError(
                            build_guidance_message(
                                what="Role is declared more than once.",
                                why="Each agent block may define role only once.",
                                fix="Keep a single role entry for the agent.",
                                example='agent "planner"\n  role is "Plans"',
                            ),
                            line=key_tok.line,
                            column=key_tok.column,
                        )
                    parser._advance()
                    parser._expect("IS", "Expected 'is' after role")
                    role_tok = parser._expect("STRING", "Expected role string")
                    role = role_tok.value
                else:
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f"Unknown field '{key_tok.value}' in agent team declaration.",
                            why="Agent blocks only allow a role field.",
                            fix='Use `role is "..."` or remove the field.',
                            example='agent "planner"\n  role is "Plans"',
                        ),
                        line=key_tok.line,
                        column=key_tok.column,
                    )
                parser._match("NEWLINE")
            parser._expect("DEDENT", "Expected end of agent block")
            members.append(
                ast.AgentTeamMember(
                    name=name_tok.value,
                    role=role,
                    line=name_tok.line,
                    column=name_tok.column,
                )
            )
            parser._match("NEWLINE")
            continue
        raise Namel3ssError("Expected agent name or agent block in team of agents", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of team block")
    return ast.AgentTeamDecl(members=members, line=team_tok.line, column=team_tok.column)


__all__ = ["parse_agent_team_decl"]
