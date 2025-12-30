from __future__ import annotations

import pytest

from namel3ss import contract as build_contract
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore


SOURCE = '''spec is "1.0"

record "Sample":
  field "min" is number must be at least 0
  field "max" is number must be at most 10
  field "range" is number must be between -5 and 5
  field "whole" is number must be an integer

flow "save":
  set state.sample.min is input.values.min
  set state.sample.max is input.values.max
  set state.sample.range is input.values.range
  set state.sample.whole is input.values.whole
  create "Sample" with state.sample as sample
'''


def _run_save(values: dict) -> None:
    contract_obj = build_contract(SOURCE)
    program = contract_obj.program
    store = MemoryStore()
    execute_program_flow(program, "save", store=store, input={"values": values})


def test_numeric_constraints_accept_valid_values() -> None:
    _run_save({"min": 0, "max": 10, "range": -5, "whole": 3})


def test_numeric_constraints_reject_invalid_values() -> None:
    with pytest.raises(Namel3ssError):
        _run_save({"min": -1, "max": 10, "range": 0, "whole": 3})
    with pytest.raises(Namel3ssError):
        _run_save({"min": 0, "max": 11, "range": 0, "whole": 3})
    with pytest.raises(Namel3ssError):
        _run_save({"min": 0, "max": 10, "range": 6, "whole": 3})
    with pytest.raises(Namel3ssError):
        _run_save({"min": 0, "max": 10, "range": 0, "whole": 1.5})
