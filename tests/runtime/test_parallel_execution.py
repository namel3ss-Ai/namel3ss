import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_parallel_tasks_run_in_name_order() -> None:
    code = """
flow "demo":
  parallel:
    run "beta":
      return 2
    run "alpha":
      return 1
"""
    result = run_flow(code)
    assert result.last_value == [1, 2]


def test_parallel_locals_merge_into_flow() -> None:
    code = """
flow "demo":
  parallel:
    run "beta":
      let beta is 2
      return beta
    run "alpha":
      let alpha is 1
      return alpha
  return alpha + beta
"""
    result = run_flow(code)
    assert result.last_value == 3


def test_parallel_is_deterministic() -> None:
    code = """
flow "demo":
  parallel:
    run "beta":
      return 2
    run "alpha":
      return 1
"""
    first = run_flow(code)
    second = run_flow(code)
    assert first.last_value == second.last_value
    assert first.traces == second.traces


def test_parallel_state_write_blocked() -> None:
    code = """
flow "demo":
  parallel:
    run "alpha":
      set state.value is 1
"""
    with pytest.raises(Namel3ssError, match="Parallel tasks cannot change state"):
        run_flow(code)
