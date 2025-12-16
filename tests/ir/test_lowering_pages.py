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
