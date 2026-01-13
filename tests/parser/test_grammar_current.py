from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_match_requires_with_block() -> None:
    source = '''flow "demo":
  match state.status:
    when "ok":
      return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert exc.value.message == "Expected 'with' inside match"


def test_match_with_block_parses() -> None:
    source = '''flow "demo":
  match state.status:
    with:
      when "ok":
        return "ok"
'''
    parse_program(source)


def test_update_allows_bare_and_quoted_field_names() -> None:
    source = '''flow "demo":
  update "Order" where id is 1 set:
    status is "done"
    "title" is "Ready"
'''
    program = parse_program(source)
    update_stmt = program.flows[0].body[0]
    assert isinstance(update_stmt, ast.Update)
    assert [field.name for field in update_stmt.updates] == ["status", "title"]


def test_ui_title_keyword_parses() -> None:
    source = '''page "home":
  title is "Welcome"
'''
    program = parse_program(source)
    item = program.pages[0].items[0]
    assert isinstance(item, ast.TitleItem)
    assert item.value == "Welcome"


def test_state_path_expression_parses_without_existence_check() -> None:
    source = '''flow "demo":
  return state.missing.value
'''
    program = parse_program(source)
    ret_stmt = program.flows[0].body[0]
    assert isinstance(ret_stmt, ast.Return)
    assert isinstance(ret_stmt.expression, ast.StatePath)
    assert ret_stmt.expression.path == ["missing", "value"]


def test_find_record_reference_parses() -> None:
    source = '''flow "demo":
  find "Order" where id is 1
'''
    program = parse_program(source)
    find_stmt = program.flows[0].body[0]
    assert isinstance(find_stmt, ast.Find)
    assert find_stmt.record_name == "Order"


def test_duplicate_ui_action_labels_parse() -> None:
    source = '''flow "demo":
  return "ok"

page "home":
  button "Save":
    calls flow "demo"
  button "Save":
    calls flow "demo"
'''
    program = parse_program(source)
    items = program.pages[0].items
    assert sum(isinstance(item, ast.ButtonItem) for item in items) == 2
