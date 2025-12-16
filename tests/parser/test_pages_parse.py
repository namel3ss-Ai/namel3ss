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
