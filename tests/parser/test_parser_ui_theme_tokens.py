import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_page_tokens_inline_parse() -> None:
    source = '''page "Theme" tokens:
  size is "compact"
  radius is "lg"
  density is "airy"
  font is "sm"
  color_scheme is "dark"
  section "Body":
    text is "Hi"
'''
    program = parse_program(source)
    page = program.pages[0]
    tokens = page.theme_tokens
    assert tokens is not None
    assert tokens.size == "compact"
    assert tokens.radius == "lg"
    assert tokens.density == "airy"
    assert tokens.font == "sm"
    assert tokens.color_scheme == "dark"


def test_page_tokens_block_must_be_first() -> None:
    source = '''page "Theme":
  title is "Late"
  tokens:
    size is "compact"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "Tokens must be declared immediately after the page header" in str(err.value)


def test_component_theme_overrides_parse() -> None:
    source = '''page "Theme":
  card "Panel":
    size is "compact"
    radius is "full"
    text is "Hello"
'''
    program = parse_program(source)
    card = program.pages[0].items[0]
    assert isinstance(card, ast.CardItem)
    overrides = card.theme_overrides
    assert overrides is not None
    assert overrides.size == "compact"
    assert overrides.radius == "full"


def test_include_theme_settings_page_parse() -> None:
    source = '''page "Theme":
  include theme_settings_page
'''
    program = parse_program(source)
    assert isinstance(program.pages[0].items[0], ast.ThemeSettingsPageItem)


def test_invalid_token_value_rejected() -> None:
    source = '''page "Theme":
  tokens:
    size is "xl"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "invalid token value" in str(err.value)
