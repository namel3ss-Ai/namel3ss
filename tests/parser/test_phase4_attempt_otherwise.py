from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


def test_attempt_otherwise_parses() -> None:
    source = '''
flow "demo":
  attempt:
    let result is "ok"
    return result
  otherwise:
    return "fallback"
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.TryCatch)
    assert stmt.catch_var == "err"


def test_try_catch_still_parses() -> None:
    source = '''
flow "demo":
  try:
    return "ok"
  with catch err:
    return "fallback"
'''
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ast.TryCatch)
    assert stmt.catch_var == "err"
