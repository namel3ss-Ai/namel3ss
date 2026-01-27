from __future__ import annotations

from pathlib import Path

from namel3ss.ingestion.policy import (
    DEFAULT_RULES,
    POLICY_FILENAME,
    PolicyRule,
    _apply_policy_decl,
    _parse_policy_toml,
    _rules_from_data,
)
from namel3ss.ir.model.policy import PolicyDecl as PolicyDeclIR, PolicyRule as PolicyRuleIR
from namel3ss.lang.policy import POLICY_SECTION_KEYS
from namel3ss.runtime.persistence_paths import resolve_project_root


def inspect_ingestion_policy(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    policy_decl: PolicyDeclIR | None = None,
) -> dict:
    root = resolve_project_root(project_root, app_path)
    rules = dict(DEFAULT_RULES)
    file_actions: set[str] = set()
    if root is not None:
        path = root / POLICY_FILENAME
        if path.exists():
            data = _parse_policy_toml(path)
            rules = _rules_from_data(data)
            file_actions = _policy_actions_from_data(data)
    if policy_decl is not None:
        rules = _apply_policy_decl(rules, policy_decl)
    sources = _policy_rule_sources(file_actions, policy_decl)
    declared = _declared_policy_rules(policy_decl)
    effective = _effective_policy_rules(rules, sources)
    return {"declared": declared, "effective": effective}


def _policy_actions_from_data(data: dict) -> set[str]:
    actions: set[str] = set()
    if not isinstance(data, dict):
        return actions
    for section, action_map in POLICY_SECTION_KEYS.items():
        section_data = data.get(section)
        if not isinstance(section_data, dict):
            continue
        for key, action in action_map.items():
            if key in section_data:
                actions.add(action)
    return actions


def _policy_rule_sources(file_actions: set[str], policy_decl: PolicyDeclIR | None) -> dict[str, str]:
    sources = {action: "default" for action in DEFAULT_RULES.keys()}
    for action in file_actions:
        sources[action] = "file"
    if policy_decl is None:
        return sources
    for rule in policy_decl.rules:
        sources[rule.action] = "declared"
    return sources


def _declared_policy_rules(policy_decl: PolicyDeclIR | None) -> list[dict]:
    if policy_decl is None:
        return []
    rules = sorted(policy_decl.rules, key=lambda rule: rule.action)
    return [_policy_rule_summary(rule.action, _rule_from_decl(rule), source=None) for rule in rules]


def _effective_policy_rules(rules: dict[str, PolicyRule], sources: dict[str, str]) -> list[dict]:
    items = []
    for action in sorted(rules.keys()):
        items.append(_policy_rule_summary(action, rules[action], source=sources.get(action, "default")))
    return items


def _rule_from_decl(rule: PolicyRuleIR) -> PolicyRule:
    if rule.mode == "allow":
        return PolicyRule.allow()
    if rule.mode == "deny":
        return PolicyRule.deny()
    return PolicyRule.require(rule.permissions)


def _policy_rule_summary(action: str, rule: PolicyRule, source: str | None) -> dict:
    entry = {
        "action": action,
        "effect": "allow" if rule.mode in {"allow", "require"} else "deny",
        "mode": rule.mode,
    }
    if rule.permissions:
        entry["requires"] = list(rule.permissions)
    if source:
        entry["source"] = source
    return entry


__all__ = ["inspect_ingestion_policy"]
