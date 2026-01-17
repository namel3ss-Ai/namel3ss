from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


SOURCE = '''page "home":
  link "Settings" to page "Settings"

page "Settings":
  text is "Configure the app."
'''


def test_link_item_parses():
    program = parse_program(SOURCE)
    link = program.pages[0].items[0]
    assert isinstance(link, ast.LinkItem)
    assert link.label == "Settings"
    assert link.page_name == "Settings"
