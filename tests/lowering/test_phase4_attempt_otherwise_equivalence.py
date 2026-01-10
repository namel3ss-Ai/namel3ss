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


def test_attempt_otherwise_ir_equivalence() -> None:
    sugar = '''
flow "demo":
  attempt:
    let result is "ok"
    return result
  otherwise:
    return "fallback"
'''
    core = '''
flow "demo":
  try:
    let result is "ok"
    return result
  with catch err:
    return "fallback"
'''
    sugar_dump = _strip_positions(dump_ir(lower_ir_program(sugar)))
    core_dump = _strip_positions(dump_ir(lower_ir_program(core)))
    assert sugar_dump == core_dump


def test_attempt_otherwise_catch_var_is_stable() -> None:
    source = '''
flow "demo":
  attempt:
    let err is "value"
    return err
  otherwise:
    return "fallback"
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.TryCatch)
    assert stmt.catch_var == "__err1"


def test_attempt_otherwise_ir_is_deterministic() -> None:
    source = '''
flow "demo":
  attempt:
    return "ok"
  otherwise:
    return "fallback"
'''
    first = dump_ir(lower_ir_program(source))
    second = dump_ir(lower_ir_program(source))
    assert first == second
