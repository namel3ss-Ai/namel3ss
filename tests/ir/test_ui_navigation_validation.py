import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_navigation_requires_capability() -> None:
    source = """spec is "1.0"

nav_sidebar:
  item "Chat" goes_to "Chat"

page "Chat":
  text is "Hello"
"""
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "capability ui_navigation" in str(exc.value)


def test_navigate_to_requires_existing_page() -> None:
    source = """spec is "1.0"

capabilities:
  ui_navigation

page "Chat":
  button "Settings":
    navigate_to "Settings"
"""
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown page" in str(exc.value).lower()


def test_navigation_lowers_when_valid() -> None:
    source = """spec is "1.0"

capabilities:
  ui_navigation

flow "noop":
  return "ok"

nav_sidebar:
  item "Chat" goes_to "Chat"
  item "Settings" goes_to "Settings"

page "Chat":
  button "Settings":
    navigate_to "Settings"

page "Settings":
  button "Back":
    go_back
"""
    program = lower_ir_program(source)
    assert getattr(program, "ui_navigation", None) is not None
    first_button = program.pages[0].items[0]
    second_button = program.pages[1].items[0]
    assert getattr(first_button, "action_kind", None) == "navigate_to"
    assert getattr(second_button, "action_kind", None) == "go_back"
