from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.theme.theme_config import parse_theme_config, serialize_theme_config
from namel3ss.ui.theme.theme_tokens import (
    THEME_BASE_ORDER,
    default_theme_tokens,
    resolve_theme_tokens,
    token_schema,
)


def test_theme_token_schema_matches_default_order() -> None:
    schema = token_schema()
    defaults = default_theme_tokens()
    assert list(schema.keys()) == list(defaults.keys())
    assert all("type" in schema[name] for name in schema)
    assert all("category" in schema[name] for name in schema)


def test_resolve_theme_tokens_is_deterministic_for_base_and_overrides() -> None:
    first = resolve_theme_tokens(
        "dark",
        {
            "primary_color": "#1F5DE1",
            "spacing_scale": 1.25,
        },
    )
    second = resolve_theme_tokens(
        "dark",
        {
            "spacing_scale": 1.25,
            "primary_color": "#1F5DE1",
        },
    )
    assert first == second
    assert first.base_theme == "dark"
    assert first.tokens["primary_color"] == "#1F5DE1"
    assert first.tokens["spacing_scale"] == 1.25


def test_parse_theme_config_normalizes_base_theme_and_overrides() -> None:
    config = parse_theme_config(
        {
            "base_theme": "high-contrast",
            "overrides": {"border_radius": 6},
        }
    )
    serialized = serialize_theme_config(config)
    assert config.base_theme == "high_contrast"
    assert config.overrides["border_radius"] == 6
    assert serialized == {
        "base_theme": "high_contrast",
        "overrides": {"border_radius": 6},
    }


def test_parse_theme_config_rejects_unknown_token() -> None:
    with pytest.raises(Namel3ssError) as err:
        parse_theme_config({"base_theme": "default", "overrides": {"primary_colour": "#112233"}})
    assert "Unknown theme token" in str(err.value)


def test_known_base_themes_are_stable() -> None:
    assert THEME_BASE_ORDER == ("default", "dark", "high_contrast")
