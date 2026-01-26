from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def _first_flow(source: str) -> ast.Flow:
    program = parse_program(source)
    return program.flows[0]


def test_escaped_identifiers_in_nested_lets() -> None:
    source = '''flow "demo":
  let `flow` is 1
  if true:
    let:
      `flow` is 2
      total is `flow` + 1
  return `flow`
'''
    flow = _first_flow(source)
    top_let = flow.body[0]
    assert isinstance(top_let, ast.Let)
    assert top_let.name == "flow"
    assert top_let.name_escaped is True
    if_stmt = flow.body[1]
    assert isinstance(if_stmt, ast.If)
    inner_lets = [stmt for stmt in if_stmt.then_body if isinstance(stmt, ast.Let)]
    assert [stmt.name for stmt in inner_lets] == ["flow", "total"]
    assert inner_lets[0].name_escaped is True
    assert inner_lets[1].name_escaped is False


def test_escaped_identifiers_in_list_binders() -> None:
    source = '''flow "demo":
  let mapped is map numbers with item as `flow`:
    `flow`
  let filtered is filter numbers with item as `title`:
    `title` is greater than 1
  let total is reduce numbers with acc as `flow` and item as `title` starting 0:
    `flow` + `title`
'''
    flow = _first_flow(source)
    lets = [stmt for stmt in flow.body if isinstance(stmt, ast.Let)]
    map_expr = lets[0].expression
    assert isinstance(map_expr, ast.ListMapExpr)
    assert map_expr.var_name == "flow"
    filter_expr = lets[1].expression
    assert isinstance(filter_expr, ast.ListFilterExpr)
    assert filter_expr.var_name == "title"
    reduce_expr = lets[2].expression
    assert isinstance(reduce_expr, ast.ListReduceExpr)
    assert reduce_expr.acc_name == "flow"
    assert reduce_expr.item_name == "title"


def test_escaped_identifiers_in_record_literal_map() -> None:
    source = '''flow "demo":
  let payload is map:
    `title` is "Hello"
    `flow` is 2
'''
    flow = _first_flow(source)
    let_stmt = flow.body[0]
    assert isinstance(let_stmt, ast.Let)
    expr = let_stmt.expression
    assert isinstance(expr, ast.MapExpr)
    keys = [entry.key.value for entry in expr.entries]
    assert keys == ["title", "flow"]


def test_escaped_identifiers_in_form_field_names() -> None:
    source = '''record "User":
  `title` text

page "home":
  form is "User":
    groups:
      group "Main":
        field `title`
    fields:
      field `title`:
        help is "Title"
'''
    program = parse_program(source)
    form = next(item for item in program.pages[0].items if isinstance(item, ast.FormItem))
    assert form.groups is not None
    assert form.groups[0].fields[0].name == "title"
    assert form.fields is not None
    assert form.fields[0].name == "title"


def test_escaped_identifiers_in_reference_names() -> None:
    source = '''record "record":
  name text

flow "demo":
  create `record` with state.name as result
'''
    flow = _first_flow(source)
    stmt = flow.body[0]
    assert isinstance(stmt, ast.Create)
    assert stmt.record_name == "record"
