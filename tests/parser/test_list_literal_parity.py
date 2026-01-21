from namel3ss.ast import nodes as ast

from tests.conftest import parse_program


def _list_items(source: str):
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    expr = stmt.expression
    assert isinstance(expr, ast.ListExpr)
    return [item.value for item in expr.items]


def test_inline_and_block_lists_match():
    inline = '''flow "demo":
  let roles is list of text: "admin", "staff"
'''
    block = '''flow "demo":
  let roles is list of text:
    "admin",
    "staff"
'''
    assert _list_items(inline) == _list_items(block)
