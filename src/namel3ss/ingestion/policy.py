from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.auth.permission_helpers import normalize_permissions, normalize_roles
from namel3ss.runtime.auth.trace_events import authorization_check_event
from namel3ss.runtime.persistence_paths import resolve_project_root


POLICY_FILENAME = "ingestion.policy.toml"

ACTION_INGESTION_RUN = "ingestion.run"
ACTION_INGESTION_REVIEW = "ingestion.review"
ACTION_INGESTION_OVERRIDE = "ingestion.override"
ACTION_INGESTION_SKIP = "ingestion.skip"
ACTION_RETRIEVAL_INCLUDE_WARN = "retrieval.include_warn"
ACTION_UPLOAD_REPLACE = "upload.replace"

_ACTION_TABLE = {
    ACTION_INGESTION_RUN: ("ingestion", "run"),
    ACTION_INGESTION_REVIEW: ("ingestion", "review"),
    ACTION_INGESTION_OVERRIDE: ("ingestion", "override"),
    ACTION_INGESTION_SKIP: ("ingestion", "skip"),
    ACTION_RETRIEVAL_INCLUDE_WARN: ("retrieval", "include_warn"),
    ACTION_UPLOAD_REPLACE: ("upload", "replace"),
}

_ACTION_LABELS = {
    ACTION_INGESTION_RUN: "Ingestion run",
    ACTION_INGESTION_REVIEW: "Ingestion review",
    ACTION_INGESTION_OVERRIDE: "Ingestion override",
    ACTION_INGESTION_SKIP: "Ingestion skip",
    ACTION_RETRIEVAL_INCLUDE_WARN: "Warn retrieval",
    ACTION_UPLOAD_REPLACE: "Upload replace",
}


def _normalize_permission_list(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    items: list[str] = []
    for item in values:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in items:
            continue
        items.append(value)
    return tuple(items)


@dataclass(frozen=True)
class PolicyRule:
    mode: str
    permissions: tuple[str, ...]

    @classmethod
    def allow(cls) -> "PolicyRule":
        return cls(mode="allow", permissions=())

    @classmethod
    def deny(cls) -> "PolicyRule":
        return cls(mode="deny", permissions=())

    @classmethod
    def require(cls, permissions: list[str] | tuple[str, ...]) -> "PolicyRule":
        return cls(mode="require", permissions=_normalize_permission_list(permissions))


@dataclass(frozen=True)
class IngestionPolicy:
    rules: dict[str, PolicyRule]
    source: str


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    allowed: bool
    reason: str | None
    required_permissions: tuple[str, ...]
    source: str


DEFAULT_RULES = {
    ACTION_INGESTION_RUN: PolicyRule.allow(),
    ACTION_INGESTION_REVIEW: PolicyRule.allow(),
    ACTION_INGESTION_OVERRIDE: PolicyRule.require([ACTION_INGESTION_OVERRIDE]),
    ACTION_INGESTION_SKIP: PolicyRule.require([ACTION_INGESTION_SKIP]),
    ACTION_RETRIEVAL_INCLUDE_WARN: PolicyRule.require([ACTION_RETRIEVAL_INCLUDE_WARN]),
    ACTION_UPLOAD_REPLACE: PolicyRule.require([ACTION_UPLOAD_REPLACE]),
}

_SECTION_KEYS = {
    "ingestion": {
        "run": ACTION_INGESTION_RUN,
        "review": ACTION_INGESTION_REVIEW,
        "override": ACTION_INGESTION_OVERRIDE,
        "skip": ACTION_INGESTION_SKIP,
    },
    "retrieval": {
        "include_warn": ACTION_RETRIEVAL_INCLUDE_WARN,
    },
    "upload": {
        "replace": ACTION_UPLOAD_REPLACE,
    },
}


def load_ingestion_policy(project_root: str | Path | None, app_path: str | Path | None) -> IngestionPolicy:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return IngestionPolicy(rules=dict(DEFAULT_RULES), source="default")
    path = root / POLICY_FILENAME
    if not path.exists():
        return IngestionPolicy(rules=dict(DEFAULT_RULES), source="default")
    data = _parse_policy_toml(path)
    rules = _rules_from_data(data)
    return IngestionPolicy(rules=rules, source=_policy_source(path, root))


def evaluate_ingestion_policy(
    policy: IngestionPolicy,
    action: str,
    identity: dict | None,
) -> PolicyDecision:
    rule = policy.rules.get(action)
    if rule is None:
        return PolicyDecision(
            action=action,
            allowed=False,
            reason="policy_missing",
            required_permissions=(),
            source=policy.source,
        )
    if rule.mode == "allow":
        return PolicyDecision(
            action=action,
            allowed=True,
            reason=None,
            required_permissions=(),
            source=policy.source,
        )
    if rule.mode == "deny":
        return PolicyDecision(
            action=action,
            allowed=False,
            reason="policy_denied",
            required_permissions=(),
            source=policy.source,
        )
    required = rule.permissions
    allowlist = set(normalize_permissions(identity)) | set(normalize_roles(identity))
    if any(permission in allowlist for permission in required):
        return PolicyDecision(
            action=action,
            allowed=True,
            reason=None,
            required_permissions=required,
            source=policy.source,
        )
    return PolicyDecision(
        action=action,
        allowed=False,
        reason="permission_missing",
        required_permissions=required,
        source=policy.source,
    )


def policy_trace(action: str, decision: PolicyDecision) -> dict:
    outcome = "allowed" if decision.allowed else "denied"
    return authorization_check_event(
        subject=f"policy:{action}",
        outcome=outcome,
        reason=decision.reason,
    )


def policy_error(action: str, decision: PolicyDecision, *, mode: str | None = None) -> Namel3ssError:
    label = _ACTION_LABELS.get(action, action)
    if mode:
        label = f"{label} ({mode})"
    if decision.reason == "permission_missing" and decision.required_permissions:
        required = ", ".join(decision.required_permissions)
        message = build_guidance_message(
            what=f"{label} is not permitted.",
            why=f"Policy requires permission {required}.",
            fix=f"Provide an identity with {required} or allow {action} in {POLICY_FILENAME}.",
            example=_policy_example(action, permissions=decision.required_permissions),
        )
    elif decision.reason == "policy_missing":
        message = build_guidance_message(
            what=f"{label} is not permitted.",
            why="Policy does not define this action.",
            fix=f"Add a rule for {action} in {POLICY_FILENAME}.",
            example=_policy_example(action, allow=True),
        )
    else:
        message = build_guidance_message(
            what=f"{label} is not permitted.",
            why="Policy denies this action.",
            fix=f"Allow {action} in {POLICY_FILENAME}.",
            example=_policy_example(action, allow=True),
        )
    details = {
        "category": "policy",
        "reason_code": decision.reason or "policy_denied",
        "action": action,
    }
    if decision.required_permissions:
        details["required_permissions"] = list(decision.required_permissions)
    return Namel3ssError(message, details=details)


def _policy_example(
    action: str,
    *,
    allow: bool | None = None,
    permissions: tuple[str, ...] | None = None,
) -> str:
    section, key = _ACTION_TABLE.get(action, ("ingestion", "run"))
    if permissions:
        value = json.dumps(list(permissions))
    elif allow is True:
        value = "true"
    else:
        value = "false"
    return f"[{section}]\n{key} = {value}"


def _policy_source(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
        return relative.as_posix()
    except Exception:
        return path.name or "policy"


def _rules_from_data(data: dict) -> dict[str, PolicyRule]:
    rules = dict(DEFAULT_RULES)
    if not isinstance(data, dict):
        return rules
    unknown_sections = [key for key in data.keys() if key not in _SECTION_KEYS]
    if unknown_sections:
        raise Namel3ssError(_unknown_section_message(unknown_sections[0]))
    for section, action_map in _SECTION_KEYS.items():
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, dict):
            raise Namel3ssError(_section_type_message(section))
        unknown_keys = [key for key in section_data.keys() if key not in action_map]
        if unknown_keys:
            raise Namel3ssError(_unknown_key_message(section, unknown_keys[0]))
        for key, action in action_map.items():
            if key not in section_data:
                continue
            rules[action] = _rule_from_value(section_data[key], section=section, key=key)
    return rules


def _rule_from_value(value: object, *, section: str, key: str) -> PolicyRule:
    if isinstance(value, bool):
        return PolicyRule.allow() if value else PolicyRule.deny()
    if isinstance(value, str) and value.strip():
        return PolicyRule.require([value.strip()])
    if isinstance(value, list):
        if any(not isinstance(item, str) for item in value):
            raise Namel3ssError(_value_type_message(section, key))
        permissions = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not permissions:
            return PolicyRule.deny()
        return PolicyRule.require(permissions)
    raise Namel3ssError(_value_type_message(section, key))


def _parse_policy_toml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if "\n" not in text and "\\n" in text:
        text = text.replace("\\n", "\n")
    try:
        import tomllib  # type: ignore
    except Exception:
        return _parse_policy_toml_minimal(text, path)
    try:
        data = tomllib.loads(text)
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{path.name} is not valid TOML.",
                why=f"TOML parsing failed: {err}.",
                fix=f"Fix the TOML syntax in {path.name}.",
                example='[ingestion]\\nrun = true',
            )
        ) from err
    return data if isinstance(data, dict) else {}


def _parse_policy_toml_minimal(text: str, path: Path) -> dict:
    current = None
    data: dict[str, object] = {}
    line_num = 0
    for raw_line in text.splitlines():
        line_num += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            current = section
            continue
        if current is None:
            continue
        if "=" not in line:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Invalid line in {path.name}.",
                    why="Expected key = value inside a section.",
                    fix="Add a key/value entry under a section header.",
                    example='run = true',
                ),
                line=line_num,
                column=1,
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        section_data = data.get(current)
        if isinstance(section_data, dict):
            section_data[key] = _parse_policy_value(value, line_num, path)
    return data


def _parse_policy_value(value: str, line_num: int, path: Path) -> object:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as err:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why=f"Array parsing failed: {err}.",
                    fix="Use a JSON-style array of strings.",
                    example='override = ["ingestion.override"]',
                ),
                line=line_num,
                column=1,
            ) from err
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported array value in {path.name}.",
                    why="Only arrays of strings are supported.",
                    fix="Provide a list of quoted strings.",
                    example='override = ["ingestion.override"]',
                ),
                line=line_num,
                column=1,
            )
        return parsed
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unsupported value in {path.name}.",
            why="Only booleans and arrays of strings are supported.",
            fix="Use true/false or a list of permissions.",
            example='review = ["ingestion.review"]',
        ),
        line=line_num,
        column=1,
    )


def _unknown_section_message(section: str) -> str:
    return build_guidance_message(
        what=f"Unsupported policy section '{section}'.",
        why="Ingestion policy supports ingestion, retrieval, and upload sections.",
        fix=f"Remove the {section} section or rename it.",
        example='[ingestion]\\nrun = true',
    )


def _section_type_message(section: str) -> str:
    return build_guidance_message(
        what=f"Policy section '{section}' must be an object.",
        why="Policy sections contain key/value rules.",
        fix=f"Use a [{section}] table with boolean or list values.",
        example=f"[{section}]\\nrun = true",
    )


def _unknown_key_message(section: str, key: str) -> str:
    return build_guidance_message(
        what=f"Unsupported policy key '{section}.{key}'.",
        why="Only known policy keys are supported.",
        fix=f"Remove {key} or rename it to a supported key.",
        example=f"[{section}]\\nrun = true",
    )


def _value_type_message(section: str, key: str) -> str:
    return build_guidance_message(
        what=f"Policy value '{section}.{key}' must be true/false or a list of strings.",
        why="Policy rules are boolean or permission lists.",
        fix="Use true/false or a list of permissions.",
        example=f"[{section}]\\n{key} = [\"permission\"]",
    )


__all__ = [
    "ACTION_INGESTION_OVERRIDE",
    "ACTION_INGESTION_REVIEW",
    "ACTION_INGESTION_RUN",
    "ACTION_INGESTION_SKIP",
    "ACTION_RETRIEVAL_INCLUDE_WARN",
    "ACTION_UPLOAD_REPLACE",
    "IngestionPolicy",
    "PolicyDecision",
    "PolicyRule",
    "load_ingestion_policy",
    "evaluate_ingestion_policy",
    "policy_error",
    "policy_trace",
]
