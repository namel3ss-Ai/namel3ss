import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, parse_program


def test_parse_layout_items_and_nesting():
    source = '''page "home":
  section "Overview":
    text is "Intro"
    row:
      column:
        card "First":
          text is "Inside card"
      column:
        text is "Second column"
  divider
  image is "logo"
'''
    program = parse_program(source)
    page = program.pages[0]
    assert isinstance(page.items[0], ast.SectionItem)
    section = page.items[0]
    assert section.label == "Overview"
    assert isinstance(section.children[0], ast.TextItem)
    row = section.children[1]
    assert isinstance(row, ast.RowItem)
    assert all(isinstance(col, ast.ColumnItem) for col in row.children)
    first_col = row.children[0]
    assert isinstance(first_col.children[0], ast.CardItem)
    card = first_col.children[0]
    assert card.label == "First"
    assert isinstance(card.children[0], ast.TextItem)
    assert isinstance(page.items[1], ast.DividerItem)
    assert isinstance(page.items[2], ast.ImageItem)


def test_row_with_non_columns_requires_layout_capability():
    source = '''page "home":
  row:
    text is "Not allowed without ui_layout"
'''
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "UI layout requires capability ui_layout" in str(err.value)
