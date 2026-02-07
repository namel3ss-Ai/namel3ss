from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def test_parse_use_plugin_and_custom_component() -> None:
    source = '''spec is "1.0"

use plugin "maps"

page "Dashboard":
  MapViewer lat: state.user.location.lat lng: state.user.location.lng
'''
    program = parse_program(source)
    assert len(program.plugin_uses) == 1
    assert program.plugin_uses[0].name == "maps"
    item = program.pages[0].items[0]
    assert isinstance(item, ast.CustomComponentItem)
    assert item.component_name == "MapViewer"
    assert [prop.name for prop in item.properties] == ["lat", "lng"]


def test_visibility_expression_parses_for_visibility_and_only_when() -> None:
    source = '''spec is "1.0"

page "Dashboard":
  title is "Admin" visible_when: state.user.role == "admin" and state.count > 0
  button "Delete":
    calls flow "Delete"
    only when state.user.role == "admin" and not state.read_only
'''
    program = parse_program(source)
    title_item = program.pages[0].items[0]
    assert isinstance(title_item.visibility, ast.BinaryOp)
    button_item = program.pages[0].items[1]
    assert isinstance(button_item.visibility_rule, ast.VisibilityExpressionRule)
    assert isinstance(button_item.visibility_rule.expression, ast.BinaryOp)
