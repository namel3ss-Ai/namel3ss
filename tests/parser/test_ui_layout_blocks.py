import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_layout_blocks_and_conditions():
    source = '''page "Demo":
  stack:
    text is "Top"
    row:
      col:
        text is "Left"
      col:
        text is "Right"
    grid columns is 2:
      text is "A"
      text is "B"
  sidebar_layout:
    sidebar:
      text is "Side"
    main:
      if state.ready:
        text is "Ready"
      else:
        text is "Not"
      drawer title is "Info" when is state.show_drawer:
        text is "Body"
  sticky bottom:
    text is "Pinned"
'''
    program = parse_program(source)
    page = program.pages[0]
    stack = page.items[0]
    assert isinstance(stack, ast.LayoutStack)
    assert isinstance(stack.children[1], ast.LayoutRow)
    row = stack.children[1]
    assert all(isinstance(child, ast.LayoutColumn) for child in row.children)
    grid = stack.children[2]
    assert isinstance(grid, ast.LayoutGrid)
    sidebar_layout = page.items[1]
    assert isinstance(sidebar_layout, ast.SidebarLayout)
    conditional = sidebar_layout.main[0]
    assert isinstance(conditional, ast.ConditionalBlock)
    assert len(conditional.then_children) == 1
    assert len(conditional.else_children or []) == 1
    drawer = sidebar_layout.main[1]
    assert isinstance(drawer, ast.LayoutDrawer)
    assert isinstance(drawer.show_when, ast.StatePath)
    assert drawer.show_when.path == ["show_drawer"]
    sticky = page.items[2]
    assert isinstance(sticky, ast.LayoutSticky)
    assert sticky.position == "bottom"


def test_row_with_columns_remains_legacy():
    source = '''page "Legacy":
  row:
    column:
      text is "One"
    column:
      text is "Two"
'''
    program = parse_program(source)
    row = program.pages[0].items[0]
    assert isinstance(row, ast.RowItem)
    assert all(isinstance(col, ast.ColumnItem) for col in row.children)


def test_show_when_parses_on_leaf_items():
    source = '''page "Show":
  text is "Hello" show_when is state.ready
'''
    program = parse_program(source)
    item = program.pages[0].items[0]
    assert isinstance(item, ast.TextItem)
    assert isinstance(item.show_when, ast.StatePath)
    assert item.show_when.path == ["ready"]


def test_sidebar_layout_requires_sidebar_and_main():
    source = '''page "Broken":
  sidebar_layout:
    sidebar:
      text is "Missing main"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "sidebar_layout must declare both sidebar and main blocks" in str(err.value)


def test_grid_columns_must_be_positive_integer():
    source = '''page "Broken":
  grid columns is 0:
    text is "Nope"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "Grid columns must be a positive integer" in str(err.value)

