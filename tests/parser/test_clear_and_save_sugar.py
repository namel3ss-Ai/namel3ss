from __future__ import annotations

from dataclasses import fields, is_dataclass

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def _strip_positions(value):
    if isinstance(value, list):
        return [_strip_positions(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_positions(item) for item in value)
    if is_dataclass(value):
        data = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name in {"line", "column"}:
                data[field.name] = None
            else:
                data[field.name] = _strip_positions(field_value)
        return type(value)(**data)
    return value


def test_clear_single_lowers_to_delete() -> None:
    sugar = '''
flow "demo":
  clear "PlannerOutput"
'''
    core = '''
flow "demo":
  delete "PlannerOutput" where true
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_clear_list_lowers_in_order() -> None:
    sugar = '''
flow "demo":
  clear:
    "PlannerOutput"
    "RunSummary"
'''
    core = '''
flow "demo":
  delete "PlannerOutput" where true
  delete "RunSummary" where true
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_save_with_lowers_to_set_and_create() -> None:
    sugar = '''
flow "demo":
  save "PlannerOutput" with:
    text is plan.text
'''
    core = '''
flow "demo":
  set state.__save_planner_output_payload with:
    text is plan.text
  create "PlannerOutput" with state.__save_planner_output_payload as planner_output
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_notice_lowers_to_state_set() -> None:
    sugar = '''
flow "demo":
  notice "Ready"
'''
    core = '''
flow "demo":
  set state.notice is "Ready"
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_save_statement_still_parses() -> None:
    source = '''
flow "demo":
  save "PlannerOutput"
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.Save)
