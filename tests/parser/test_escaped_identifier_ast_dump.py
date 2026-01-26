from __future__ import annotations

from tests.conftest import parse_program
from tests.spec_freeze.helpers.ast_dump import dump_ast


def test_escaped_identifier_ast_dump_is_stable() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let `flow` is 1\n'
    program = parse_program(source)
    let_stmt = program.flows[0].body[0]
    assert dump_ast(let_stmt) == {
        "type": "Let",
        "line": 4,
        "column": 3,
        "name": "flow",
        "expression": {
            "type": "Literal",
            "line": 4,
            "column": 17,
            "value": "1",
        },
        "constant": False,
        "name_escaped": True,
    }
