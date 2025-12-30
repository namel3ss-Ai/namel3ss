import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program, run_flow


GOLDEN_FLOW = '''spec is "1.0"

flow "demo":
  let x is 10
  if x is greater than 5:
    set state.result is "ok"
  else:
    set state.result is "no"
'''


def test_golden_flow_parses_lowers_and_executes():
    program_ir = lower_ir_program(GOLDEN_FLOW)
    assert len(program_ir.flows) == 1
    flow = program_ir.flows[0]
    assert flow.name == "demo"
    assert isinstance(flow.body[0], ir.Let)
    assert isinstance(flow.body[1], ir.If)

    result = run_flow(GOLDEN_FLOW)
    assert result.state["result"] == "ok"


def test_end_to_end_return_from_loop():
    source = '''flow "ret":
  repeat up to 5 times:
    return "done"
    set state.result is "unreachable"
'''
    result = run_flow(source, flow_name="ret")
    assert result.last_value == "done"
    assert "result" not in result.state


def test_end_to_end_try_catch_sets_message():
    source = '''flow "trycatch":
  try:
    set state.result is missing_var
  with catch error:
    set state.result is error.message
'''
    result = run_flow(source, flow_name="trycatch")
    assert "unknown variable" in result.state["result"].lower()

