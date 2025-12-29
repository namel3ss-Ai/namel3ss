import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.parser.core import parse


def test_parser_error_render_includes_caret_and_line() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let x is\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    rendered = format_error(excinfo.value, source)
    assert str(excinfo.value) in rendered
    assert "let x is" in rendered
    assert "^" in rendered


def test_lexer_error_render_includes_caret_and_line() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  @bad\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    rendered = format_error(excinfo.value, source)
    assert '@bad' in rendered
    assert '^' in rendered
    assert str(excinfo.value) in rendered


def test_runtime_error_render_includes_caret_and_line() -> None:
    from namel3ss.ir import nodes as ir
    from namel3ss.runtime.executor import execute_flow

    flow = ir.Flow(
        name="demo",
        body=[
            ir.Set(
                target=ir.VarReference(name="x", line=2, column=3),
                expression=ir.Literal(value=1, line=2, column=18),
                line=2,
                column=3,
            )
        ],
        line=1,
        column=1,
    )
    with pytest.raises(Namel3ssError) as excinfo:
        execute_flow(flow)
    rendered = format_error(excinfo.value, 'spec is "1.0"\n\nflow "demo":\n  set x is 1\n')
    assert "Runtime error." in rendered
    assert "line: 2" in rendered
    assert "^" in rendered
    assert str(excinfo.value) in rendered
