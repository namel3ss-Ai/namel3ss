from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


SOURCE = '''record "Order":
  name text
  status text
  icon text

flow "open_order":
  return "ok"

page "home":
  list is "Order":
    variant is icon
    item:
      primary is name
      secondary is status
      icon is icon
    empty_text is "No orders yet."
    selection is single
    actions:
      action "Open":
        calls flow "open_order"
'''

PLAIN_ICON_SOURCE = '''record "Project":
  name text
  icon text

flow "open_project":
  return "ok"

page "home":
  list is "Project":
    variant is icon_plain
    item:
      primary is name
      icon is icon
    actions:
      action "Open":
        calls flow "open_project"
'''


def test_parse_list_block():
    program = parse_program(SOURCE)
    list_item = next(item for item in program.pages[0].items if isinstance(item, ast.ListItem))
    assert list_item.record_name == "Order"
    assert list_item.variant == "icon"
    assert list_item.empty_text == "No orders yet."
    assert list_item.selection == "single"
    assert list_item.item is not None
    assert list_item.item.primary == "name"
    assert list_item.item.secondary == "status"
    assert list_item.item.icon == "icon"
    assert list_item.actions is not None
    assert list_item.actions[0].label == "Open"


def test_parse_list_minimal():
    source = '''record "Order":
  name text

page "home":
  list is "Order"
'''
    program = parse_program(source)
    list_item = next(item for item in program.pages[0].items if isinstance(item, ast.ListItem))
    assert list_item.record_name == "Order"
    assert list_item.variant is None
    assert list_item.item is None


def test_parse_list_icon_plain_variant():
    program = parse_program(PLAIN_ICON_SOURCE)
    list_item = next(item for item in program.pages[0].items if isinstance(item, ast.ListItem))
    assert list_item.record_name == "Project"
    assert list_item.variant == "icon_plain"
    assert list_item.item is not None
    assert list_item.item.icon == "icon"
