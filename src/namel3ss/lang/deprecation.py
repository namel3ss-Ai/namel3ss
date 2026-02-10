from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.validation import add_warning
from namel3ss.version import get_version
from namel3ss.versioning.semver import version_sort_key


@dataclass(frozen=True)
class DeprecationRule:
    rule_id: str
    token: str
    replacement: str
    deprecated_in: str
    error_in: str
    summary: str

    def warning_code(self) -> str:
        return f"deprecation.{self.rule_id}"

    def warning_message(self) -> str:
        return (
            f"{self.summary} '{self.token}' is deprecated since {self.deprecated_in}; "
            f"use '{self.replacement}'."
        )

    def fix_message(self) -> str:
        return (
            f"Replace '{self.token}' with '{self.replacement}'. "
            f"This warning becomes an error in {self.error_in}."
        )


DEPRECATION_RULES: tuple[DeprecationRule, ...] = (
    DeprecationRule(
        rule_id="capability.custom_theme",
        token="custom_theme",
        replacement="ui.theming",
        deprecated_in="1.0.0",
        error_in="2.0.0",
        summary="Capability token",
    ),
    DeprecationRule(
        rule_id="capability.custom_ui",
        token="custom_ui",
        replacement="ui.plugins",
        deprecated_in="1.0.0",
        error_in="2.0.0",
        summary="Capability token",
    ),
    DeprecationRule(
        rule_id="capability.ui_theme",
        token="ui_theme",
        replacement="ui.theming",
        deprecated_in="1.0.0",
        error_in="2.0.0",
        summary="Capability token",
    ),
)


def deprecation_rules() -> tuple[DeprecationRule, ...]:
    return tuple(sorted(DEPRECATION_RULES, key=lambda item: item.rule_id))


def find_capability_deprecations(capabilities: tuple[str, ...] | list[str] | set[str] | None) -> tuple[DeprecationRule, ...]:
    if not capabilities:
        return ()
    normalized = {str(item).strip() for item in capabilities if str(item).strip()}
    return tuple(rule for rule in deprecation_rules() if rule.token in normalized)


def append_capability_deprecation_warnings(
    capabilities: tuple[str, ...] | list[str] | set[str] | None,
    warnings: list | None,
    *,
    current_version: str | None = None,
) -> None:
    if warnings is None:
        return
    active = find_capability_deprecations(capabilities)
    version = _normalize_version(current_version or get_version())
    for rule in active:
        if _is_error_version(rule, version):
            raise Namel3ssError(
                (
                    f"Deprecated capability '{rule.token}' is no longer supported in {version}. "
                    f"Use '{rule.replacement}'."
                )
            )
        add_warning(
            warnings,
            code=rule.warning_code(),
            message=rule.warning_message(),
            fix=rule.fix_message(),
            category="deprecation",
            enforced_at=rule.error_in,
        )


def _is_error_version(rule: DeprecationRule, current_version: str) -> bool:
    return version_sort_key(current_version) >= version_sort_key(_normalize_version(rule.error_in))


def _normalize_version(value: str) -> str:
    return str(value or "").strip().removeprefix("v")


__all__ = [
    "DEPRECATION_RULES",
    "DeprecationRule",
    "append_capability_deprecation_warnings",
    "deprecation_rules",
    "find_capability_deprecations",
]
