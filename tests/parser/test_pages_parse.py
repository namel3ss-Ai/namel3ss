from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


SOURCE = '''record "User":
  email string must be unique
  name string must be present

flow "create_user":
  return "ok"

page "home":
  title is "Welcome"
  text is "Hello"
  form is "User"
  table is "User"
  button "Create user":
    calls flow "create_user"
'''

SHOW_SOURCE = '''page "home":
  show table from state matches
    list from state selected
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

def test_parse_pages_and_items():
    program = parse_program(SOURCE)
    assert len(program.pages) == 1
    page = program.pages[0]
    assert page.name == "home"
    assert isinstance(page.items[0], ast.TitleItem)
    assert isinstance(page.items[1], ast.TextItem)
    assert isinstance(page.items[2], ast.FormItem)
    assert isinstance(page.items[3], ast.TableItem)
    assert isinstance(page.items[4], ast.ButtonItem)


def test_parse_show_state_list_and_table():
    program = parse_program(SHOW_SOURCE)
    page = program.pages[0]
    assert len(page.items) == 2
    table = page.items[0]
    list_item = page.items[1]
    assert isinstance(table, ast.TableItem)
    assert isinstance(list_item, ast.ListItem)
    assert table.record_name is None
    assert list_item.record_name is None
    assert table.source.path == ["matches"]
    assert list_item.source.path == ["selected"]


def test_parse_text_input_item():
    program = parse_program(INPUT_SOURCE)
    page = program.pages[0]
    assert len(page.items) == 1
    item = page.items[0]
    assert isinstance(item, ast.TextInputItem)
    assert item.name == "question"
    assert item.flow_name == "answer"
