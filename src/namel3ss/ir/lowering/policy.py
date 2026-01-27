from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.policy import PolicyDecl, PolicyRule


def lower_policy(policy: ast.PolicyDecl | None) -> PolicyDecl | None:
    if policy is None:
        return None
    rules = [
        PolicyRule(
            action=rule.action,
            mode=rule.mode,
            permissions=tuple(rule.permissions),
            line=rule.line,
            column=rule.column,
        )
        for rule in policy.rules
    ]
    return PolicyDecl(rules=rules, line=policy.line, column=policy.column)


__all__ = ["lower_policy"]
