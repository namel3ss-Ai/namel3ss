from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from tests.conftest import lower_ir_program, run_flow


SOURCE = '''record "Order":
  total number

flow "demo":
  create "Order" with state.order as order
  return order
'''


def test_create_saves_record_and_returns_result():
    initial_state = {"order": {"total": Decimal("12.50")}}
    result = run_flow(SOURCE, initial_state=initial_state)
    assert result.last_value["total"] == Decimal("12.50")


def test_create_rejects_non_object_values():
    bad = '''record "Order":
  total number

flow "demo":
  create "Order" with 12 as order
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(bad)
    expected = (
        "What happened: Create expects a record dictionary of values.\n"
        "Why: The provided value is number, but create needs key/value fields to validate and save.\n"
        "Fix: Pass a dictionary (for example, state.order or an input payload).\n"
        'Example: create "Order" with state.order as order'
    )
    assert excinfo.value.message == expected


def test_create_persists_with_sqlite(tmp_path):
    program = lower_ir_program(SOURCE)
    store = SQLiteStore(tmp_path / "data.db")
    initial_state = {"order": {"total": Decimal("9.99")}}
    result = run_flow(SOURCE, initial_state=initial_state, store=store)
    records = store.list_records(program.records[0])
    store.close()
    assert result.last_value["total"] == Decimal("9.99")
    assert records[0]["total"] == Decimal("9.99")
