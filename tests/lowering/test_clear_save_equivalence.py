from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import lower_ir_program, parse_program
from tests.spec_freeze.helpers.ir_dump import dump_ir


def _strip_positions(value):
    if isinstance(value, list):
        return [_strip_positions(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_positions(val) for key, val in value.items() if key not in {"line", "column"}}
    return value


def test_clear_save_notice_ir_equivalence() -> None:
    sugar = '''
flow "demo":
  clear:
    "PlannerOutput"
    "RunSummary"
  save "PlannerOutput" with:
    text is "Plan"
  notice "Ready"
'''
    core = '''
flow "demo":
  delete "PlannerOutput" where true
  delete "RunSummary" where true
  set state.__save_planner_output_payload with:
    text is "Plan"
  create "PlannerOutput" with state.__save_planner_output_payload as planner_output
  set state.notice is "Ready"
'''
    sugar_dump = _strip_positions(dump_ir(lower_ir_program(sugar)))
    core_dump = _strip_positions(dump_ir(lower_ir_program(core)))
    assert sugar_dump == core_dump


def test_save_sugar_uses_stable_names() -> None:
    source = '''
flow "demo":
  save "RunSummary" with:
    seq is 1
    label is "Generate plan"
'''
    program = parse_program(source)
    body = program.flows[0].body
    set_targets = [stmt.target.path for stmt in body if isinstance(stmt, ast.Set)]
    assert set_targets
    assert all(path[0] == "__save_run_summary_payload" for path in set_targets)
    create_stmt = next(stmt for stmt in body if isinstance(stmt, ast.Create))
    assert create_stmt.target == "run_summary"


def test_save_sugar_ir_is_deterministic() -> None:
    source = '''
flow "demo":
  save "PlannerOutput" with:
    text is "Plan"
'''
    first = dump_ir(lower_ir_program(source))
    second = dump_ir(lower_ir_program(source))
    assert first == second
