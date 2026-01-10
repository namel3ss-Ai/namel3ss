from __future__ import annotations

from dataclasses import fields, is_dataclass

from tests.conftest import lower_ir_program, parse_program, run_flow
from tests.spec_freeze.helpers.ir_dump import dump_ir


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
    if isinstance(value, str) and value.startswith("__latest_"):
        return "__latest_name"
    return value


def test_latest_sugar_lowers_to_find_last() -> None:
    sugar = '''
flow "demo":
  let brief is latest "ProjectBrief"
'''
    core = '''
flow "demo":
  find "ProjectBrief" where true
  let __latest_projectbrief_count is list length of projectbrief_results
  if __latest_projectbrief_count is greater than 0:
    let __latest_projectbrief_index is __latest_projectbrief_count - 1
    let brief is list get projectbrief_results at __latest_projectbrief_index
  else:
    let brief is null
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_require_latest_sugar_lowers() -> None:
    sugar = '''
flow "demo":
  require latest "ProjectBrief" as brief otherwise "Add a project description."
'''
    core = '''
flow "demo":
  find "ProjectBrief" where true
  let __latest_projectbrief_count is list length of projectbrief_results
  if __latest_projectbrief_count is 0:
    set state.status.message is "Add a project description."
    return "missing_project_brief"
  let __latest_projectbrief_index is __latest_projectbrief_count - 1
  let brief is list get projectbrief_results at __latest_projectbrief_index
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_require_latest_missing_returns_sentinel() -> None:
    source = '''
record "ProjectBrief":
  field "description" is text must be present

flow "demo":
  require latest "ProjectBrief" as brief otherwise "Add a project description."
  return brief.description
'''
    result = run_flow(source)
    assert result.last_value == "missing_project_brief"
    status = result.state.get("status") if isinstance(result.state, dict) else None
    message = status.get("message") if isinstance(status, dict) else None
    assert message == "Add a project description."


def test_latest_ir_is_deterministic() -> None:
    source = '''
record "ProjectBrief":
  field "description" is text must be present

flow "demo":
  require latest "ProjectBrief" as brief otherwise "Add a project description."
  return "ok"
'''
    first = dump_ir(lower_ir_program(source))
    second = dump_ir(lower_ir_program(source))
    assert first == second


def test_map_get_and_list_get_still_parse() -> None:
    source = '''
flow "demo":
  let first is list get items at 0
  let name is map get item key "name"
  return name
'''
    parse_program(source)
