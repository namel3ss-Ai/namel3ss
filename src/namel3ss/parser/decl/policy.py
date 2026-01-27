from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.policy import POLICY_ACTIONS
from namel3ss.parser.expr.common import read_attr_name


_RULE_MODES = {"allow", "deny", "require"}


def parse_policy_decl(parser) -> ast.PolicyDecl:
    policy_tok = parser._advance()
    parser._expect("NEWLINE", "Expected newline after policy")
    parser._expect("INDENT", "Expected indented policy block")
    rules: list[ast.PolicyRuleDecl] = []
    seen_actions: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        mode_tok = parser._current()
        if mode_tok.type == "IDENT":
            parser._advance()
            mode = mode_tok.value
        elif mode_tok.type == "REQUIRE":
            parser._advance()
            mode = "require"
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="Expected policy rule (allow/deny/require).",
                    why="Policy rules start with allow, deny, or require.",
                    fix="Start the line with allow, deny, or require.",
                    example="policy\n  allow ingestion.run",
                ),
                line=mode_tok.line,
                column=mode_tok.column,
            )
        if mode not in _RULE_MODES:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown policy rule '{mode}'.",
                    why="Policy rules must start with allow, deny, or require.",
                    fix="Use allow, deny, or require before the action.",
                    example="policy\n  allow ingestion.run",
                ),
                line=mode_tok.line,
                column=mode_tok.column,
            )
        action = _parse_policy_action(parser)
        if action in seen_actions:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Policy action '{action}' is declared more than once.",
                    why="Each policy action can only be declared once.",
                    fix="Remove the duplicate rule.",
                    example="policy\n  deny ingestion.override",
                ),
                line=mode_tok.line,
                column=mode_tok.column,
            )
        permissions: list[str] = []
        if mode == "require":
            if not parser._match("WITH"):
                raise Namel3ssError(
                    build_guidance_message(
                        what="Policy require is missing permissions.",
                        why="Require rules must include a with clause.",
                        fix="Add `with <permission>` after the action.",
                        example="policy\n  require ingestion.override with ingestion.override",
                    ),
                    line=mode_tok.line,
                    column=mode_tok.column,
                )
            permissions = _parse_permissions(parser)
            if not permissions:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Policy require needs at least one permission.",
                        why="Require rules list the permissions that allow the action.",
                        fix="Provide one or more permissions after with.",
                        example="policy\n  require ingestion.override with ingestion.override",
                    ),
                    line=mode_tok.line,
                    column=mode_tok.column,
                )
        _expect_policy_line_end(parser, mode_tok)
        seen_actions.add(action)
        rules.append(
            ast.PolicyRuleDecl(
                action=action,
                mode=mode,
                permissions=permissions,
                line=mode_tok.line,
                column=mode_tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of policy block")
    while parser._match("NEWLINE"):
        pass
    return ast.PolicyDecl(rules=rules, line=policy_tok.line, column=policy_tok.column)


def _parse_policy_action(parser) -> str:
    tok = parser._current()
    action = _parse_dotted_name(parser, context="policy action")
    if action not in POLICY_ACTIONS:
        allowed = ", ".join(sorted(POLICY_ACTIONS))
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown policy action '{action}'.",
                why=f"Policy actions must be one of: {allowed}.",
                fix="Use a supported policy action.",
                example="policy\n  allow ingestion.run",
            ),
            line=tok.line,
            column=tok.column,
        )
    return action


def _parse_permissions(parser) -> list[str]:
    permissions: list[str] = []
    while True:
        if parser._current().type in {"NEWLINE", "DEDENT"}:
            break
        permission = _parse_permission_value(parser)
        permissions.append(permission)
        if parser._match("COMMA"):
            if parser._current().type in {"NEWLINE", "DEDENT"}:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Trailing comma in policy permissions.",
                        why="Permissions must be listed as values separated by commas.",
                        fix="Remove the trailing comma or add another permission.",
                        example="policy\n  require ingestion.override with ingestion.override, admin",
                    ),
                    line=parser._current().line,
                    column=parser._current().column,
                )
            continue
        break
    return permissions


def _parse_permission_value(parser) -> str:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return tok.value
    return _parse_dotted_name(parser, context="permission name")


def _parse_dotted_name(parser, *, context: str) -> str:
    parts = [read_attr_name(parser, context=context)]
    while parser._match("DOT"):
        parts.append(read_attr_name(parser, context=context))
    return ".".join(parts)


def _expect_policy_line_end(parser, tok) -> None:
    if parser._match("NEWLINE"):
        return
    if parser._current().type == "DEDENT":
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Unexpected token in policy rule.",
            why="Policy rules must end after the action or permissions.",
            fix="Move extra tokens to their own line.",
            example="policy\n  allow ingestion.run",
        ),
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_policy_decl"]
