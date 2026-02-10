from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.deprecation import (
    append_capability_deprecation_warnings,
    find_capability_deprecations,
)
from namel3ss.validation import ValidationWarning


def test_find_capability_deprecations_is_deterministic() -> None:
    rules = find_capability_deprecations(("ui_theme", "custom_ui", "custom_theme", "http"))
    assert [rule.rule_id for rule in rules] == [
        "capability.custom_theme",
        "capability.custom_ui",
        "capability.ui_theme",
    ]


def test_append_capability_deprecation_warnings_emits_sorted_warnings() -> None:
    warnings: list[ValidationWarning] = []
    append_capability_deprecation_warnings(
        ("custom_ui", "ui_theme", "http"),
        warnings,
        current_version="1.0.0",
    )
    codes = [warning.code for warning in warnings]
    assert codes == [
        "deprecation.capability.custom_ui",
        "deprecation.capability.ui_theme",
    ]
    assert all(warning.category == "deprecation" for warning in warnings)
    assert all(warning.enforced_at == "2.0.0" for warning in warnings)


def test_append_capability_deprecation_warnings_escalates_after_error_version() -> None:
    warnings: list[ValidationWarning] = []
    with pytest.raises(Namel3ssError):
        append_capability_deprecation_warnings(
            ("ui_theme",),
            warnings,
            current_version="2.0.0",
        )
