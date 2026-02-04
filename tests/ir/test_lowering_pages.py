from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''record "User":
  email string must be unique

flow "create_user":
  return "ok"

page "home":
  title is "Welcome"
  text is "Hello"
  form is "User"
  table is "User"
  button "Create":
    calls flow "create_user"
'''

STATE_SOURCE = '''page "home":
  table from state metrics:
    columns:
      include name
      label name is "Name"
  list from state items:
    item:
      primary is name
'''

INPUT_SOURCE = '''contract flow "answer":
  input:
    question is text
  output:
    result is text

flow "answer":
  return "ok"

page "home":
  input text as question
    send to flow "answer"
'''

def test_lowering_includes_pages_and_items():
    program = lower_ir_program(SOURCE)
    assert program.pages
    page = program.pages[0]
    assert page.name == "home"
    assert isinstance(page.items[0], ir.TitleItem)
    assert isinstance(page.items[1], ir.TextItem)
    assert isinstance(page.items[2], ir.FormItem)
    assert isinstance(page.items[3], ir.TableItem)
    assert isinstance(page.items[4], ir.ButtonItem)


def test_lowering_state_list_and_table():
    program = lower_ir_program(STATE_SOURCE)
    page = program.pages[0]
    table = page.items[0]
    list_item = page.items[1]
    assert isinstance(table, ir.TableItem)
    assert isinstance(list_item, ir.ListItem)
    assert table.record_name is None
    assert list_item.record_name is None
    assert table.source.path == ["metrics"]
    assert list_item.source.path == ["items"]


def test_lowering_text_input_item():
    program = lower_ir_program(INPUT_SOURCE)
    page = program.pages[0]
    item = page.items[0]
    assert isinstance(item, ir.TextInputItem)
    assert item.name == "question"
    assert item.flow_name == "answer"
