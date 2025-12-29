from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.runtime.executor.api import execute_program_flow


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_module_file_merges_items(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "math.ai"
    _write(
        module_path,
        (
            'define function "add":\n'
            '  input:\n'
            '    a is number\n'
            '    b is number\n'
            '  return a + b\n\n'
            'record "Item":\n'
            '  field "name" is text\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'use module "modules/math.ai" as math\n\n'
            'flow "demo":\n'
            '  return call function "add":\n'
            '    a is 1\n'
            '    b is 2\n'
        ),
    )
    project = load_project(app_path)
    assert "add" in project.program.functions
    record_names = [rec.name for rec in project.program.records]
    assert "Item" in record_names
    summary = getattr(project.program, "module_summary", {})
    assert summary.get("merge_order") == ["math"]


def test_module_only_filters_categories(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "only.ai"
    _write(
        module_path,
        (
            'define function "add":\n'
            '  input:\n'
            '    a is number\n'
            '    b is number\n'
            '  return a + b\n\n'
            'record "Item":\n'
            '  field "name" is text\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'use module "modules/only.ai" as only\n'
            'only:\n'
            '  functions\n\n'
            'flow "demo":\n'
            '  return call function "add":\n'
            '    a is 1\n'
            '    b is 2\n'
        ),
    )
    project = load_project(app_path)
    assert "add" in project.program.functions
    record_names = [rec.name for rec in project.program.records]
    assert "Item" not in record_names


def test_module_conflict_requires_override(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "conflict.ai"
    _write(
        module_path,
        (
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 2\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 1\n\n'
            'use module "modules/conflict.ai" as conflict\n\n'
            'flow "demo":\n'
            '  return call function "value":\n'
            '    x is 1\n'
        ),
    )
    with pytest.raises(Namel3ssError):
        load_project(app_path)


def test_module_allow_override_wins(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_one = tmp_path / "modules" / "one.ai"
    module_two = tmp_path / "modules" / "two.ai"
    _write(
        module_one,
        (
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 1\n'
        ),
    )
    _write(
        module_two,
        (
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 2\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'use module "modules/one.ai" as one\n'
            'use module "modules/two.ai" as two\n'
            'allow override:\n'
            '  functions\n\n'
            'flow "demo":\n'
            '  return call function "value":\n'
            '    x is 1\n'
        ),
    )
    project = load_project(app_path)
    result = execute_program_flow(project.program, "demo", state={}, input={})
    assert result.last_value == 2
