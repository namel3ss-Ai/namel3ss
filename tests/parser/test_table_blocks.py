from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


SOURCE = '''record "Order":
  name text
  status text

flow "open_order":
  return "ok"

page "home":
  table is "Order":
    columns:
      include name
      label name is "Customer"
      exclude status
    empty_text is "No orders yet."
    sort:
      by is name
      order is desc
    pagination:
      page_size is 5
    selection is single
    row_actions:
      row_action "Open":
        calls flow "open_order"
'''


def test_parse_table_block():
    program = parse_program(SOURCE)
    table = next(item for item in program.pages[0].items if isinstance(item, ast.TableItem))
    assert table.record_name == "Order"
    assert table.empty_text == "No orders yet."
    assert table.selection == "single"
    assert table.sort is not None
    assert table.sort.by == "name"
    assert table.sort.order == "desc"
    assert table.pagination is not None
    assert table.pagination.page_size == 5
    assert table.columns is not None
    assert [entry.kind for entry in table.columns] == ["include", "label", "exclude"]
    assert table.row_actions is not None
    assert table.row_actions[0].label == "Open"
