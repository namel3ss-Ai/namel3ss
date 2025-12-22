import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.statements import ThemeChange as IRThemeChange
from tests.conftest import lower_ir_program, parse_program


def test_parse_set_theme_statement():
    source = 'flow "demo":\n  set theme to "dark"\n'
    program = parse_program(source)
    stmt = program.flows[0].body[0]
    assert stmt.value == "dark"
    assert stmt.line is not None


def test_invalid_theme_value_raises():
    source = 'flow "demo":\n  set theme to "blue"\n'
    with pytest.raises(Namel3ssError):
        parse_program(source)


def test_lowering_theme_change_and_flag():
    source = 'flow "demo":\n  set theme to "dark"\n'
    program_ir = lower_ir_program(source)
    stmt = program_ir.flows[0].body[0]
    assert isinstance(stmt, IRThemeChange)
    assert stmt.value == "dark"
    assert program_ir.theme_runtime_supported is True
