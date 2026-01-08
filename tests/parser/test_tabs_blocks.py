import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_tabs_block_with_default():
    source = '''record "Order":
  name text

page "home":
  tabs:
    default is "Details"
    tab "Overview":
      text is "One"
    tab "Details":
      table is "Order"
'''
    program = parse_program(source)
    tabs = program.pages[0].items[0]
    assert isinstance(tabs, ast.TabsItem)
    assert tabs.default == "Details"
    assert len(tabs.tabs) == 2
    assert tabs.tabs[0].label == "Overview"
    assert tabs.tabs[1].label == "Details"


def test_tabs_rejects_non_tab_children():
    source = '''page "home":
  tabs:
    text is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "tabs may only contain tab entries" in str(exc.value).lower()


def test_tabs_rejects_duplicate_labels():
    source = '''page "home":
  tabs:
    tab "Same":
      text is "One"
    tab "Same":
      text is "Two"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "duplicated" in str(exc.value).lower()


def test_tabs_rejects_invalid_default():
    source = '''page "home":
  tabs:
    default is "Missing"
    tab "One":
      text is "One"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "default tab" in str(exc.value).lower()


def test_tabs_rejects_nested_tabs():
    source = '''page "home":
  tabs:
    tab "One":
      tabs:
        tab "Inner":
          text is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "page root" in str(exc.value).lower()


def test_tab_outside_tabs_errors():
    source = '''page "home":
  tab "One":
    text is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "inside a tabs block" in str(exc.value).lower()
