from __future__ import annotations

import pytest

from namel3ss.ast.statements import KeepFirst, OrderList
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.statements import KeepFirst as IRKeepFirst
from namel3ss.ir.model.statements import OrderList as IROrderList
from tests.conftest import lower_ir_program, parse_program


def test_parse_order_and_keep_first():
    source = 'spec is "1.0"\n\nflow "demo":\n  order state.items by score from highest to lowest\n  keep first 3 items\n'
    program = parse_program(source)
    stmt0 = program.flows[0].body[0]
    stmt1 = program.flows[0].body[1]
    assert isinstance(stmt0, OrderList)
    assert stmt0.field == "score"
    assert stmt0.direction == "desc"
    assert isinstance(stmt1, KeepFirst)


def test_lowering_order_and_keep_first():
    source = 'spec is "1.0"\n\nflow "demo":\n  order state.items by score from lowest to highest\n  keep first 2 items\n'
    program = lower_ir_program(source)
    stmt0 = program.flows[0].body[0]
    stmt1 = program.flows[0].body[1]
    assert isinstance(stmt0, IROrderList)
    assert stmt0.field == "score"
    assert stmt0.direction == "asc"
    assert isinstance(stmt1, IRKeepFirst)


def test_invalid_order_direction_raises():
    source = 'spec is "1.0"\n\nflow "demo":\n  order state.items by score from highest to highest\n'
    with pytest.raises(Namel3ssError):
        parse_program(source)
