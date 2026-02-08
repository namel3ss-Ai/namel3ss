import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_debug_only_on_page_and_button():
    source = '''flow "run":
  return "ok"

page "home":
  debug_only: true
  button "Debug" debug_only is true:
    calls flow "run"
  button "Live":
    calls flow "run"
'''
    program = parse_program(source)
    page = program.pages[0]
    assert page.debug_only is True

    debug_button = page.items[0]
    live_button = page.items[1]
    assert isinstance(debug_button, ast.ButtonItem)
    assert isinstance(live_button, ast.ButtonItem)
    assert debug_button.debug_only is True
    assert live_button.debug_only is None


def test_parse_debug_only_category_on_page_and_button():
    source = '''flow "run":
  return "ok"

page "home":
  debug_only: "trace"
  button "Debug" debug_only is "metrics":
    calls flow "run"
'''
    page = parse_program(source).pages[0]
    button = page.items[0]
    assert page.debug_only == "trace"
    assert isinstance(button, ast.ButtonItem)
    assert button.debug_only == "metrics"


def test_debug_only_requires_boolean_literal_in_page_metadata():
    source = '''page "home":
  debug_only: "true"
  title is "Home"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "debug_only category must be one of" in str(exc.value)


def test_debug_only_requires_boolean_literal_in_item_metadata():
    source = '''flow "run":
  return "ok"

page "home":
  button "Run" debug_only is state.flag:
    calls flow "run"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "debug_only must be a boolean literal or diagnostics category string" in str(exc.value)
