from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''flow "ctrl":
  repeat up to 1 times:
    return true
  for each item in state.items:
    set state.value is item
  match state.value:
    with:
      when 1:
        set state.one is 1
      otherwise:
        set state.other is 0
  try:
    set state.err is missing
  with catch error:
    set state.msg is error.message
'''


def test_lowering_creates_control_flow_ir_nodes():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    assert isinstance(flow.body[0], ir.Repeat)
    assert isinstance(flow.body[0].body[0], ir.Return)
    assert isinstance(flow.body[1], ir.ForEach)
    assert isinstance(flow.body[2], ir.Match)
    assert isinstance(flow.body[3], ir.TryCatch)
    match_stmt = flow.body[2]
    assert len(match_stmt.cases) == 1
    assert match_stmt.otherwise is not None
