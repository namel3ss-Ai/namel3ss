import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


SOURCE = """spec is "1.0"

capabilities:
  ui_navigation

flow "noop":
  return "ok"

nav_sidebar:
  item "Chat" goes_to "Chat"
  item "Settings" goes_to "Settings"

page "Chat":
  button "Open settings":
    navigate_to "Settings"

page "Settings":
  button "Back":
    go_back
"""


def test_navigation_sidebar_and_button_actions_parse() -> None:
    program = parse_program(SOURCE)
    nav = getattr(program, "ui_navigation", None)
    assert isinstance(nav, ast.NavigationSidebar)
    assert [item.label for item in nav.items] == ["Chat", "Settings"]
    assert [item.page_name for item in nav.items] == ["Chat", "Settings"]
    open_settings = program.pages[0].items[0]
    assert isinstance(open_settings, ast.ButtonItem)
    assert open_settings.action_kind == "navigate_to"
    assert open_settings.target == "Settings"
    back = program.pages[1].items[0]
    assert isinstance(back, ast.ButtonItem)
    assert back.action_kind == "go_back"


def test_page_level_navigation_sidebar_parses() -> None:
    source = """spec is "1.0"

page "Home":
  nav_sidebar:
    item "Home" goes_to "Home"
  text is "Welcome"
"""
    program = parse_program(source)
    page_nav = getattr(program.pages[0], "ui_navigation", None)
    assert isinstance(page_nav, ast.NavigationSidebar)
    assert page_nav.items[0].label == "Home"


def test_navigation_item_requires_goes_to() -> None:
    source = """spec is "1.0"

nav_sidebar:
  item "Home" go_to "Home"

page "Home":
  text is "Welcome"
"""
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Navigation items must use" in str(exc.value)
