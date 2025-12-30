from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program, run_flow


def test_set_with_block_desugars_to_sets():
    sugar = """
flow "demo":
  set state.order with:
    order_id is "O-1"
    customer is "Acme"
"""
    expanded = """
flow "demo":
  set state.order.order_id is "O-1"
  set state.order.customer is "Acme"
"""
    sugar_result = run_flow(sugar)
    expanded_result = run_flow(expanded)
    assert sugar_result.state == expanded_result.state
    assert sugar_result.state == {"order": {"order_id": "O-1", "customer": "Acme"}}


def test_set_with_block_mixes_with_other_statements():
    source = """
flow "demo":
  let marker is "start"
  set state.order with:
    order_id is "O-2"
    region is "West"
  set state.status is "ready"
  return state.status
"""
    result = run_flow(source)
    assert result.last_value == "ready"
    assert result.state["order"]["region"] == "West"


def test_set_with_block_requires_state_path_base():
    source = """
flow "demo":
  let order is map
  set order with:
    order_id is "O-1"
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "state path" in str(excinfo.value).lower()


def test_set_with_block_requires_assignments():
    source = """
flow "demo":
  set state.order with:
  return "ok"
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "set block has no assignments" in str(excinfo.value).lower()


def test_set_with_block_rejects_duplicate_fields():
    source = """
flow "demo":
  set state.order with:
    order_id is "O-1"
    order_id is "O-2"
"""
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "duplicate field" in str(excinfo.value).lower()
