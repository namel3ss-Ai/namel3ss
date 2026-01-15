from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_declarative_flow_steps() -> None:
    source = '''
flow "demo"
  input
    name is text
  require "state.ready"
  create "User"
    name is input.name
  update "User"
    where "id is 1"
    set
      name is "Ada"
  delete "User"
    where "id is 2"
'''.lstrip()
    program = parse_program(source)
    flow = program.flows[0]
    assert flow.declarative is True
    assert flow.body == []
    steps = flow.steps or []
    assert len(steps) == 5
    assert isinstance(steps[0], ast.FlowInput)
    assert steps[0].fields[0].name == "name"
    assert isinstance(steps[1], ast.FlowRequire)
    assert steps[1].condition == "state.ready"
    assert isinstance(steps[2], ast.FlowCreate)
    assert steps[2].record_name == "User"
    assert isinstance(steps[3], ast.FlowUpdate)
    assert steps[3].selector == "id is 1"
    assert isinstance(steps[4], ast.FlowDelete)
    assert steps[4].selector == "id is 2"


def test_declarative_flow_unknown_step_suggests() -> None:
    source = '''
flow "demo"
  creat "User"
    name is "Ada"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    message = str(exc.value)
    assert "Unknown flow step" in message
    assert "Did you mean 'create'" in message


def test_declarative_flow_rejects_imperative_step() -> None:
    source = '''
flow "demo"
  let count is 1
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Declarative flows do not support" in str(exc.value)


def test_input_block_duplicate_fields_errors() -> None:
    source = '''
flow "demo"
  input
    name is text
    name is text
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Input field 'name' is duplicated" in str(exc.value)


def test_input_block_invalid_type_errors() -> None:
    source = '''
flow "demo"
  input
    name is banana
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Expected input field type" in str(exc.value)
