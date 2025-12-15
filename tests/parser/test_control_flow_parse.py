from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


CONTROL_SOURCE = '''flow "control":
  repeat up to 2 times:
    let x is 1
  for each item in state.items:
    set state.last is item
  match state.last:
    with:
      when 1:
        set state.status is "one"
      when 2:
        set state.status is "two"
      otherwise:
        set state.status is "other"
'''


def test_parse_control_flow_constructs():
    program = parse_program(CONTROL_SOURCE)
    flow = program.flows[0]
    assert isinstance(flow.body[0], ast.Repeat)
    assert isinstance(flow.body[1], ast.ForEach)
    match_stmt = flow.body[2]
    assert isinstance(match_stmt, ast.Match)
    assert len(match_stmt.cases) == 2
    assert match_stmt.otherwise is not None


def test_parse_try_catch_and_attr_access():
    source = '''flow "trycatch":
  try:
    set state.result is missing_var
  with catch error:
    set state.result is error.message
'''
    program = parse_program(source)
    flow = program.flows[0]
    assert isinstance(flow.body[0], ast.TryCatch)
    catch_set = flow.body[0].catch_body[0]
    assert isinstance(catch_set, ast.Set)
    assert isinstance(catch_set.expression, ast.AttrAccess)

