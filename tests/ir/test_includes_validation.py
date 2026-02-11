from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.validation.includes_validation import (
    MISSING_INCLUDES_CAPABILITY_MESSAGE,
    normalize_include_warnings,
)
from namel3ss.module_loader import load_project
from namel3ss.parser.program_loader import IncludeWarning
from tests.conftest import parse_program


def test_missing_composition_capability_is_hard_error() -> None:
    source = """
include "modules/flows.ai"

flow "demo":
  return "ok"
""".lstrip()
    program = parse_program(source)
    with pytest.raises(Namel3ssError) as err:
        from namel3ss.ir.validation.includes_validation import ensure_include_capability

        ensure_include_capability(program)
    assert MISSING_INCLUDES_CAPABILITY_MESSAGE in str(err.value)


def test_duplicate_include_warning_sort_order_is_stable() -> None:
    warnings = [
        IncludeWarning(
            code="composition.duplicate_include",
            message='Warning: Duplicate include ignored: "modules/b.ai"',
            file="app.ai",
            line=9,
            column=3,
        ),
        IncludeWarning(
            code="composition.duplicate_include",
            message='Warning: Duplicate include ignored: "modules/a.ai"',
            file="app.ai",
            line=7,
            column=3,
        ),
    ]
    normalized = normalize_include_warnings(warnings)
    assert [entry["message"] for entry in normalized] == [
        'Warning: Duplicate include ignored: "modules/a.ai"',
        'Warning: Duplicate include ignored: "modules/b.ai"',
    ]


def test_include_cycle_reports_stable_cycle_path(tmp_path) -> None:
    root = tmp_path
    app = root / "app.ai"
    child = root / "modules" / "child.ai"
    child.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/child.ai"

flow "demo":
  return "ok"
""".lstrip(),
        encoding="utf-8",
    )
    child.write_text(
        """
include "modules/child.ai"
""".lstrip(),
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError) as err:
        load_project(app)
    assert str(err.value) == "Compile error: include cycle detected: modules/child.ai -> modules/child.ai"
