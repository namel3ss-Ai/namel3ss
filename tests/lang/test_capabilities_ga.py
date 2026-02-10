from __future__ import annotations

from namel3ss.lang.capabilities import (
    has_ui_theming_capability,
    normalize_builtin_capability,
    normalize_capability_tokens,
)


def test_ui_theming_capability_supports_legacy_and_ga_tokens() -> None:
    assert normalize_builtin_capability("ui.theming") == "ui.theming"
    assert normalize_builtin_capability("ui_theme") == "ui_theme"
    assert has_ui_theming_capability(("ui_theme",))
    assert has_ui_theming_capability(("ui.theming",))


def test_normalize_capability_tokens_is_sorted_and_unique() -> None:
    tokens = normalize_capability_tokens(("ui.plugins", "ui.custom_layouts", "ui.plugins"))
    assert tokens == ("ui.custom_layouts", "ui.plugins")
