from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lexer.tokens import KEYWORDS
from namel3ss.parser.core import parse
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml


QUALITY_FILENAME = "quality.yaml"
DEFAULT_NAMING = "snake_case"
DEFAULT_MAX_FIELD_LENGTH = 64
DEFAULT_REQUIRED_FIELDS: tuple[str, ...] = ()
DEFAULT_DISALLOWED_PROMPT_WORDS: tuple[str, ...] = ()
_ALLOWED_KEYS = {
    "naming_convention",
    "naming",
    "max_field_length",
    "schema",
    "disallowed_prompt_words",
    "prompts",
    "required_fields",
}
_NAMING_ALLOWED_KEYS = {"enforce_snake_case"}
_SCHEMA_ALLOWED_KEYS = {"max_field_length", "required_fields"}
_PROMPTS_ALLOWED_KEYS = {"disallow_words", "disallowed_words", "disallowed_prompt_words"}
_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class QualityRules:
    naming_convention: str
    max_field_length: int
    disallowed_prompt_words: tuple[str, ...]
    required_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "naming_convention": self.naming_convention,
            "max_field_length": self.max_field_length,
            "disallowed_prompt_words": list(self.disallowed_prompt_words),
            "required_fields": list(self.required_fields),
        }


@dataclass(frozen=True)
class QualityIssue:
    code: str
    entity: str
    location: str
    issue: str
    suggestion: str
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "entity": self.entity,
            "location": self.location,
            "issue": self.issue,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


def quality_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / QUALITY_FILENAME


def load_quality_rules(project_root: str | Path | None, app_path: str | Path | None) -> QualityRules:
    path = quality_path(project_root, app_path)
    if path is None or not path.exists():
        return _default_rules()
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_quality_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_quality_message(path, "expected YAML mapping"))

    unknown = sorted([str(key) for key in payload.keys() if str(key) not in _ALLOWED_KEYS])
    if unknown:
        joined = ", ".join(unknown)
        raise Namel3ssError(_invalid_quality_message(path, f"unknown keys: {joined}"))

    naming_block = _mapping(payload.get("naming"), path=path, label="naming", allowed_keys=_NAMING_ALLOWED_KEYS)
    schema_block = _mapping(payload.get("schema"), path=path, label="schema", allowed_keys=_SCHEMA_ALLOWED_KEYS)
    prompts_block = _mapping(payload.get("prompts"), path=path, label="prompts", allowed_keys=_PROMPTS_ALLOWED_KEYS)

    naming = str(payload.get("naming_convention") or DEFAULT_NAMING).strip().lower()
    if naming_block is not None:
        enforce_snake_case = bool(naming_block.get("enforce_snake_case", True))
        naming = "snake_case" if enforce_snake_case else "none"
    if naming not in {"snake_case", "none"}:
        raise Namel3ssError(_invalid_quality_message(path, "naming_convention must be snake_case or none"))

    max_field_length = (schema_block or {}).get("max_field_length", payload.get("max_field_length", DEFAULT_MAX_FIELD_LENGTH))
    if isinstance(max_field_length, bool):
        raise Namel3ssError(_invalid_quality_message(path, "max_field_length must be a positive number"))
    try:
        max_field_length = int(max_field_length)
    except Exception as err:
        raise Namel3ssError(_invalid_quality_message(path, "max_field_length must be a positive number")) from err
    if max_field_length <= 0:
        raise Namel3ssError(_invalid_quality_message(path, "max_field_length must be a positive number"))

    prompt_words_source = (prompts_block or {}).get(
        "disallow_words",
        (prompts_block or {}).get("disallowed_words", (prompts_block or {}).get("disallowed_prompt_words", payload.get("disallowed_prompt_words"))),
    )
    required_fields_source = (schema_block or {}).get("required_fields", payload.get("required_fields"))

    disallowed_prompt_words = _parse_word_list(prompt_words_source, "disallowed_prompt_words", path)
    required_fields = _parse_word_list(required_fields_source, "required_fields", path)

    return QualityRules(
        naming_convention=naming,
        max_field_length=max_field_length,
        disallowed_prompt_words=disallowed_prompt_words,
        required_fields=required_fields,
    )


def run_quality_checks(
    source: str,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> dict[str, object]:
    rules = load_quality_rules(project_root, app_path)
    issues = _collect_issues(source, rules)
    return {
        "ok": len(issues) == 0,
        "count": len(issues),
        "rules": rules.to_dict(),
        "issues": [issue.to_dict() for issue in issues],
    }


def suggest_quality_fixes(payload: dict[str, object]) -> list[str]:
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return []
    suggestions: list[str] = []
    seen: set[str] = set()
    for item in issues:
        if not isinstance(item, dict):
            continue
        suggestion = str(item.get("suggestion") or "").strip()
        if not suggestion or suggestion in seen:
            continue
        seen.add(suggestion)
        suggestions.append(suggestion)
    return suggestions


def _collect_issues(source: str, rules: QualityRules) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    try:
        program = parse(source)
    except Exception as err:
        issues.append(
            QualityIssue(
                code="quality.parse_error",
                entity="program",
                location="app.ai",
                issue=f"Could not parse source: {err}",
                suggestion="Fix parser errors first.",
            )
        )
        return issues

    reserved = set(KEYWORDS.keys())

    for flow in sorted(getattr(program, "flows", []) or [], key=lambda item: item.name):
        _check_name(issues, f"flow:{flow.name}", flow.name, rules, reserved)

    for route in sorted(getattr(program, "routes", []) or [], key=lambda item: item.name):
        _check_name(issues, f"route:{route.name}", route.name, rules, reserved)
        _check_route_fields(issues, route, rules)

    for record in sorted(getattr(program, "records", []) or [], key=lambda item: item.name):
        _check_name(issues, f"record:{record.name}", record.name, rules, reserved)
        _check_required_record_fields(issues, record, rules)
        for field in sorted(record.fields, key=lambda item: item.name):
            _check_name(issues, f"record:{record.name}", field.name, rules, reserved)
            _check_field_type(issues, f"record:{record.name}.{field.name}", getattr(field, "type_name", ""))
            _check_length(issues, f"record:{record.name}.{field.name}", field.name, rules.max_field_length)

    for prompt in sorted(getattr(program, "prompts", []) or [], key=lambda item: item.name):
        _check_name(issues, f"prompt:{prompt.name}", prompt.name, rules, reserved)
        _check_prompt_bias(issues, f"prompt:{prompt.name}", getattr(prompt, "text", ""), rules)

    for ai_decl in sorted(getattr(program, "ais", []) or [], key=lambda item: item.name):
        _check_name(issues, f"ai:{ai_decl.name}", ai_decl.name, rules, reserved)
        _check_prompt_bias(issues, f"ai:{ai_decl.name}", getattr(ai_decl, "system_prompt", "") or "", rules)

    issues.sort(key=lambda item: (item.entity, item.location, item.code, item.issue))
    return issues


def _check_name(
    issues: list[QualityIssue],
    entity: str,
    name: str,
    rules: QualityRules,
    reserved: set[str],
) -> None:
    _check_length(issues, entity, name, rules.max_field_length)
    lowered = name.strip().lower()
    if lowered in reserved:
        issues.append(
            QualityIssue(
                code="quality.reserved_name",
                entity=entity,
                location=name,
                issue=f"Name '{name}' is reserved.",
                suggestion="Rename this item to a non-reserved snake_case name.",
            )
        )
    if rules.naming_convention == "snake_case" and not _SNAKE_CASE_RE.match(name):
        issues.append(
            QualityIssue(
                code="quality.naming",
                entity=entity,
                location=name,
                issue=f"Name '{name}' is not snake_case.",
                suggestion="Use lower case letters, numbers, and underscores only.",
            )
        )


def _check_length(issues: list[QualityIssue], entity: str, value: str, limit: int) -> None:
    if len(value) <= limit:
        return
    issues.append(
        QualityIssue(
            code="quality.max_field_length",
            entity=entity,
            location=value,
            issue=f"Value is too long ({len(value)} > {limit}).",
            suggestion=f"Shorten this value to at most {limit} characters.",
        )
    )


def _check_field_type(issues: list[QualityIssue], location: str, type_name: str) -> None:
    if isinstance(type_name, str) and type_name.strip():
        return
    issues.append(
        QualityIssue(
            code="quality.schema_type_missing",
            entity=location,
            location=location,
            issue="Field type is missing.",
            suggestion="Add a field type like text, number, boolean, json, list, or map.",
        )
    )


def _check_route_fields(issues: list[QualityIssue], route, rules: QualityRules) -> None:
    route_entity = f"route:{route.name}"
    for group_name, fields in (
        ("parameters", route.parameters),
        ("request", route.request or {}),
        ("response", route.response),
    ):
        for field_name, field in sorted((fields or {}).items(), key=lambda item: item[0]):
            _check_name(issues, route_entity, field_name, rules, set(KEYWORDS.keys()))
            _check_field_type(issues, f"{route_entity}.{group_name}.{field_name}", getattr(field, "type_name", ""))


def _check_required_record_fields(issues: list[QualityIssue], record, rules: QualityRules) -> None:
    if not rules.required_fields:
        return
    existing = {field.name for field in record.fields}
    for required in rules.required_fields:
        if required in existing:
            continue
        issues.append(
            QualityIssue(
                code="quality.required_field_missing",
                entity=f"record:{record.name}",
                location=required,
                issue=f"Required field '{required}' is missing.",
                suggestion=f"Add '{required}' to record {record.name}.",
            )
        )


def _check_prompt_bias(issues: list[QualityIssue], entity: str, text: str, rules: QualityRules) -> None:
    lowered = str(text or "").lower()
    for word in rules.disallowed_prompt_words:
        needle = word.lower()
        if not needle:
            continue
        if needle in lowered:
            issues.append(
                QualityIssue(
                    code="quality.bias_word",
                    entity=entity,
                    location=word,
                    issue=f"Disallowed word '{word}' was found.",
                    suggestion="Rewrite this text to remove that word.",
                )
            )


def _mapping(
    value: object,
    *,
    path: Path,
    label: str,
    allowed_keys: set[str],
) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_quality_message(path, f"{label} must be a mapping"))
    unknown = sorted([str(key) for key in value.keys() if str(key) not in allowed_keys])
    if unknown:
        joined = ", ".join(unknown)
        raise Namel3ssError(_invalid_quality_message(path, f"{label} has unknown keys: {joined}"))
    return value


def _parse_word_list(value: object, key: str, path: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise Namel3ssError(_invalid_quality_message(path, f"{key} must be a list of text values"))
    items: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        items.append(text)
    return tuple(sorted(set(items), key=lambda item: item.lower()))


def _default_rules() -> QualityRules:
    return QualityRules(
        naming_convention=DEFAULT_NAMING,
        max_field_length=DEFAULT_MAX_FIELD_LENGTH,
        disallowed_prompt_words=DEFAULT_DISALLOWED_PROMPT_WORDS,
        required_fields=DEFAULT_REQUIRED_FIELDS,
    )


def _invalid_quality_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="quality.yaml is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Use naming/schema/prompts blocks or flat naming_convention/max_field_length/disallowed_prompt_words/required_fields keys.",
        example=(
            "naming:\n"
            "  enforce_snake_case: true\n"
            "schema:\n"
            "  max_field_length: 64\n"
            "prompts:\n"
            "  disallow_words:\n"
            "    - violent"
        ),
    )


__all__ = [
    "QUALITY_FILENAME",
    "QualityIssue",
    "QualityRules",
    "load_quality_rules",
    "quality_path",
    "run_quality_checks",
    "suggest_quality_fixes",
]
