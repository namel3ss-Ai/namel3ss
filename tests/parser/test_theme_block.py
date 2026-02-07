from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_theme_block_parses_into_definition() -> None:
    source = '''
theme:
  preset: "clarity"
  harmonize: false
  density: "compact"
  brand_palette:
    brand_primary: "#6200EE"
    functional_error: "red"
  tokens:
    color.primary: color.brand_primary.600
    color.error: color.functional_error.500
page "home":
  title is "Hello"
'''
    program = parse_program(source)
    theme = getattr(program, "theme_definition", None)
    assert theme is not None
    assert theme.preset == "clarity"
    assert theme.harmonize is False
    assert theme.density == "compact"
    assert theme.brand_palette["brand_primary"] == "#6200EE"
    assert theme.tokens["color.primary"] == "color.brand_primary.600"


def test_theme_block_must_be_before_pages() -> None:
    source = '''
page "home":
  title is "Hello"
theme:
  preset: "clarity"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "before page definitions" in str(exc.value)


def test_theme_block_duplicate_rejected() -> None:
    source = '''
theme:
  preset: "clarity"
theme:
  preset: "calm"
page "home":
  title is "Hello"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Theme is already declared" in str(exc.value)

