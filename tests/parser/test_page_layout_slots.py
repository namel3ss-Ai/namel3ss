import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_page_layout_slots():
    source = '''page "chat":
  layout:
    header:
      title is "Support Inbox"
    sidebar_left:
      section "Folders":
        text is "Open"
    main:
      section "Messages":
        text is "Thread"
    drawer_right:
      section "Details":
        text is "Metadata"
    footer:
      text is "v1"
'''
    program = parse_program(source)
    page = program.pages[0]
    assert isinstance(page.layout, ast.PageLayout)
    assert isinstance(page.layout.header[0], ast.TitleItem)
    assert isinstance(page.layout.sidebar_left[0], ast.SectionItem)
    assert isinstance(page.layout.main[0], ast.SectionItem)
    assert isinstance(page.layout.drawer_right[0], ast.SectionItem)
    assert isinstance(page.layout.footer[0], ast.TextItem)
    assert len(page.items) == 5


def test_layout_slot_allows_explicit_empty_block():
    source = '''page "home":
  layout:
    header:
    main:
      title is "Main"
'''
    page = parse_program(source).pages[0]
    assert isinstance(page.layout, ast.PageLayout)
    assert page.layout.header == []
    assert isinstance(page.layout.main[0], ast.TitleItem)


def test_layout_rejects_unknown_slot_name():
    source = '''page "home":
  layout:
    sidebar:
      text is "x"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "unknown layout slot" in str(err.value).lower()


def test_layout_rejects_duplicate_slot():
    source = '''page "home":
  layout:
    main:
      text is "one"
    main:
      text is "two"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "already declared" in str(err.value).lower()


def test_layout_rejects_top_level_items_outside_layout():
    source = '''page "home":
  layout:
    main:
      text is "inside"
  text is "outside"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "outside layout" in str(err.value).lower()
