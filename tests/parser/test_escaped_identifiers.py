from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def test_escaped_identifier_in_let_and_reference() -> None:
    source = """
flow "demo":
  let `title` is "x"
  return `title`
"""
    program = parse_program(source)
    let_stmt = program.flows[0].body[0]
    assert isinstance(let_stmt, ast.Let)
    assert let_stmt.name == "title"
    assert let_stmt.name_escaped is True
    ret_stmt = program.flows[0].body[1]
    assert isinstance(ret_stmt, ast.Return)
    assert isinstance(ret_stmt.expression, ast.VarReference)
    assert ret_stmt.expression.name == "title"


def test_escaped_identifier_in_map_literal() -> None:
    source = """
flow "demo":
  let payload is map:
    `title` is "Hello"
"""
    program = parse_program(source)
    let_stmt = program.flows[0].body[0]
    assert isinstance(let_stmt, ast.Let)
    expr = let_stmt.expression
    assert isinstance(expr, ast.MapExpr)
    assert expr.entries[0].key.value == "title"


def test_escaped_identifier_in_record_field() -> None:
    source = """
record "Order":
  fields:
    `flow` is text
"""
    program = parse_program(source)
    record = program.records[0]
    assert record.fields[0].name == "flow"


def test_escaped_identifier_in_form_field() -> None:
    source = """
record "Order":
  fields:
    order_id is text

page "home":
  form is "Order":
    fields:
      field `title`:
        help is "Title"
"""
    program = parse_program(source)
    form = program.pages[0].items[0]
    assert isinstance(form, ast.FormItem)
    assert form.fields
    assert form.fields[0].name == "title"
