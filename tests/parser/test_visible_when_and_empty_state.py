from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_visible_when_for_page_and_section() -> None:
    source = '''spec is "1.0"

page "home": visible when state.show_home
  section "Gate" visible when state.ready:
    text is "Visible content"
'''
    program = parse_program(source)
    page = program.pages[0]
    assert isinstance(page.visibility, ast.StatePath)
    section = page.items[0]
    assert isinstance(section, ast.SectionItem)
    assert isinstance(section.visibility, ast.StatePath)


def test_parse_empty_state_hidden_and_false() -> None:
    source = '''spec is "1.0"

page "home":
  list from state.items:
    item:
      primary is name
    empty_state: hidden
  table from state.rows:
    columns:
      include name
    empty_state: false
'''
    program = parse_program(source)
    list_item = program.pages[0].items[0]
    table_item = program.pages[0].items[1]

    assert isinstance(list_item, ast.ListItem)
    assert list_item.empty_state_hidden is True
    assert list_item.empty_text is None

    assert isinstance(table_item, ast.TableItem)
    assert table_item.empty_state_hidden is True
    assert table_item.empty_text is None


def test_visible_when_duplicate_clause_is_rejected() -> None:
    source = '''spec is "1.0"

page "home":
  title is "Hi" visibility is state.ready when is state.enabled
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Visibility is declared more than once." in str(exc.value)


def test_empty_state_rejects_invalid_inline_value() -> None:
    source = '''spec is "1.0"

page "home":
  list from state.items:
    item:
      primary is name
    empty_state: true
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "empty_state inline value only supports hidden or false." in str(exc.value)
