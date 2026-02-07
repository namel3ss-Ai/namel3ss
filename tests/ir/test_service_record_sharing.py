from __future__ import annotations

from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

record "LocalNote":
  value text

record "SharedCounter" shared:
  value number

flow "demo":
  return "ok"
'''


def test_lowering_marks_shared_records() -> None:
    program = lower_ir_program(SOURCE)
    record_map = {record.name: record for record in program.records}
    assert record_map["LocalNote"].shared is False
    assert record_map["SharedCounter"].shared is True
