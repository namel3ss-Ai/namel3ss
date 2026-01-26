from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def test_escaped_identifiers_parse_in_lets_records_and_forms() -> None:
    source = '''record "User":
  `flow` text

page "home":
  form is "User":
    fields:
      field `flow`:
        help is "Flow name"

flow "demo":
  let `flow` is "x"
'''
    program = parse_program(source)
    let_stmt = program.flows[0].body[0]
    assert isinstance(let_stmt, ast.Let)
    assert let_stmt.name == "flow"
    assert let_stmt.name_escaped is True
    assert program.records[0].fields[0].name == "flow"
    form = next(item for item in program.pages[0].items if isinstance(item, ast.FormItem))
    assert form.fields is not None
    assert form.fields[0].name == "flow"
