import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, parse_program


SOURCE = '''flow "demo":
  if total is at least 10:
    return true
  if total is at most 5:
    return false
  if total is not 3:
    return true
'''


def test_condition_comparison_kinds():
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]
    assert flow.body[0].condition.kind == "gte"
    assert flow.body[1].condition.kind == "lte"
    assert flow.body[2].condition.kind == "ne"


def test_if_indentation_guidance_error():
    source = 'flow "demo":\n  if true:\n  return "bad"\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    expected = (
        "What happened: Expected an indented block after 'if'.\n"
        "Why: Blocks in namel3ss are defined by indentation after a ':' header.\n"
        "Fix: Indent the statements under the block (two spaces is typical).\n"
        'Example: if total is greater than 10:\n  set state.tier is "pro"'
    )
    assert excinfo.value.message == expected
