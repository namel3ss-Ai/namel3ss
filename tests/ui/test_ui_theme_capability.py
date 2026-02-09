import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_ui_theme_requires_capability_for_tokens() -> None:
    source = '''spec is "1.0"

page "Theme" tokens:
  size is "compact"
'''
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Token customization requires capability ui_theme" in str(err.value)


def test_ui_theme_requires_capability_for_overrides() -> None:
    source = '''spec is "1.0"

page "Theme":
  card "Panel":
    size is "compact"
    text is "Hi"
'''
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Token customization requires capability ui_theme" in str(err.value)


def test_ui_theme_requires_capability_for_settings_page() -> None:
    source = '''spec is "1.0"

page "Theme":
  include theme_settings_page
'''
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Token customization requires capability ui_theme" in str(err.value)


def test_ui_theme_tokens_with_capability() -> None:
    source = '''spec is "1.0"

capabilities:
  ui_theme

page "Theme" tokens:
  size is "compact"
  radius is "sm"
'''
    program = lower_ir_program(source)
    assert program.pages
