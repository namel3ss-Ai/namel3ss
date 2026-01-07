from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.format import format_source
from namel3ss.module_loader import load_project
from namel3ss.parser.core import parse
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.run_pipeline import build_flow_payload
from tests.spec_freeze.helpers.ast_dump import dump_ast


SURFACE_PATH = Path("tests/fixtures/expression_surface_v1.ai")
AST_GOLDEN_PATH = Path("tests/fixtures/expression_surface_v1_ast.json")


def test_expression_surface_ast_golden() -> None:
    source = SURFACE_PATH.read_text(encoding="utf-8")
    program = parse(source)
    actual = dump_ast(program)
    expected = json.loads(AST_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert actual == expected


def test_expression_surface_format_idempotent() -> None:
    source = SURFACE_PATH.read_text(encoding="utf-8")
    formatted = format_source(source)
    assert formatted == source
    assert format_source(formatted) == formatted


def test_expression_surface_runtime_results() -> None:
    project = load_project(SURFACE_PATH)
    result = execute_program_flow(project.program, "surface")
    assert isinstance(result.last_value, dict)
    assert result.last_value == {
        "size": 5,
        "first": Decimal("1"),
        "doubled": [Decimal("2"), Decimal("4"), Decimal("6"), Decimal("20")],
        "big": [Decimal("6"), Decimal("20")],
        "total": Decimal("26"),
        "avg": Decimal("13"),
        "sum_all": Decimal("16"),
        "min_val": Decimal("1"),
        "max_val": Decimal("10"),
        "median_val": Decimal("2.5"),
        "pow": Decimal("-4"),
        "pow_paren": Decimal("4"),
        "pow_chain": Decimal("512"),
        "combo": Decimal("18"),
        "mod_val": Decimal("2"),
        "div_val": Decimal("2.5"),
        "gt_ok": True,
        "lt_ok": True,
        "gte_ok": True,
        "lte_ok": True,
        "between_ok": True,
        "strict_ok": True,
        "not_between": False,
    }


def test_expression_surface_rejects_equals_outside_calc() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  let value is 1 = 2\n'
    with pytest.raises(Namel3ssError):
        parse(source)


@pytest.mark.parametrize("op_name", ["sum", "min", "max", "mean", "median"])
def test_expression_surface_empty_list_errors(op_name: str, tmp_path: Path) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        '  let numbers is state.numbers\n'
        f'  let value is {op_name}(numbers)\n'
        '  return value\n'
    )
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    project = load_project(app_file)
    outcome = build_flow_payload(project.program, "demo", state={"numbers": []}, source=source)
    payload = outcome.payload
    assert payload.get("ok") is False
    details = payload.get("details") or {}
    cause = details.get("cause") or {}
    assert cause.get("error_id") == "math.empty_list"
    assert cause.get("operation") == op_name
