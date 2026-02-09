from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


_DOMAIN_ACTIONS: dict[str, tuple[str, ...]] = {
    "ai": ("call", "tools"),
    "uploads": ("read", "write"),
    "ui_state": ("persistent_write",),
    "navigation": ("change_page",),
}
_DECISION_VALUES = {"allowed": True, "denied": False}


def parse_permissions_decl(parser) -> ast.AppPermissionsDecl:
    header = parser._expect("IDENT", "Expected 'permissions'")
    if header.value != "permissions":
        raise Namel3ssError("permissions block must start with 'permissions:'.", line=header.line, column=header.column)
    parser._expect("COLON", "Expected ':' after permissions")
    parser._expect("NEWLINE", "Expected newline after permissions header")
    parser._expect("INDENT", "Expected indented permissions block")
    domains: list[ast.AppPermissionDomainDecl] = []
    seen_domains: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        domain = _parse_permission_domain(parser)
        if domain.domain in seen_domains:
            raise Namel3ssError(
                f"permissions domain '{domain.domain}' is already declared.",
                line=domain.line,
                column=domain.column,
            )
        seen_domains.add(domain.domain)
        domains.append(domain)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of permissions block")
    while parser._match("NEWLINE"):
        continue
    if not domains:
        raise Namel3ssError("permissions block must declare at least one domain.", line=header.line, column=header.column)
    return ast.AppPermissionsDecl(domains=domains, line=header.line, column=header.column)


def _parse_permission_domain(parser) -> ast.AppPermissionDomainDecl:
    domain_tok = _expect_permission_name(parser, "Expected permission domain")
    domain = str(domain_tok.value or "")
    allowed_actions = _DOMAIN_ACTIONS.get(domain)
    if allowed_actions is None:
        raise Namel3ssError(
            f"Unknown permissions domain '{domain}'.",
            line=domain_tok.line,
            column=domain_tok.column,
        )
    parser._expect("COLON", "Expected ':' after permission domain")
    parser._expect("NEWLINE", "Expected newline after permission domain")
    parser._expect("INDENT", "Expected indented permission actions")
    actions: list[ast.AppPermissionActionDecl] = []
    seen_actions: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        action = _parse_permission_action(parser, domain=domain, allowed_actions=set(allowed_actions))
        if action.action in seen_actions:
            raise Namel3ssError(
                f"permissions action '{domain}.{action.action}' is already declared.",
                line=action.line,
                column=action.column,
            )
        seen_actions.add(action.action)
        actions.append(action)
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of permissions domain block")
    if not actions:
        raise Namel3ssError(
            f"permissions domain '{domain}' must declare at least one action.",
            line=domain_tok.line,
            column=domain_tok.column,
        )
    return ast.AppPermissionDomainDecl(domain=domain, actions=actions, line=domain_tok.line, column=domain_tok.column)


def _parse_permission_action(parser, *, domain: str, allowed_actions: set[str]) -> ast.AppPermissionActionDecl:
    action_tok = _expect_permission_name(parser, "Expected permission action")
    action = str(action_tok.value or "")
    if action not in allowed_actions:
        allowed = ", ".join(sorted(allowed_actions))
        raise Namel3ssError(
            f"Unknown permissions action '{domain}.{action}'. Allowed actions: {allowed}.",
            line=action_tok.line,
            column=action_tok.column,
        )
    parser._expect("COLON", "Expected ':' after permission action")
    decision_tok = _expect_permission_name(parser, "Expected allowed or denied")
    decision = str(decision_tok.value or "")
    if decision not in _DECISION_VALUES:
        raise Namel3ssError(
            "Permission decision must be 'allowed' or 'denied'.",
            line=decision_tok.line,
            column=decision_tok.column,
        )
    if parser._current().type not in {"NEWLINE", "DEDENT"}:
        extra = parser._current()
        raise Namel3ssError(
            "Permission lines must end after allowed/denied.",
            line=extra.line,
            column=extra.column,
        )
    return ast.AppPermissionActionDecl(
        action=action,
        allowed=_DECISION_VALUES[decision],
        line=action_tok.line,
        column=action_tok.column,
    )


def _expect_permission_name(parser, message: str):
    tok = parser._current()
    if tok.type in {"NEWLINE", "DEDENT", "INDENT", "COLON"}:
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    parser._advance()
    value = str(tok.value or "")
    if not value:
        raise Namel3ssError(message, line=tok.line, column=tok.column)
    return tok


__all__ = ["parse_permissions_decl"]
