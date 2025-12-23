from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_module_exports_flow_and_record(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        'use "inventory" as inv\n'
        'page "home":\n'
        '  button "Calc":\n'
        '    calls flow "inv.calc_total"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    record "Product"\n'
        '    flow "calc_total"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'record "Product":\n'
        "  sku text\n\n"
        'flow "calc_total":\n'
        "  return 42\n",
    )
    project = load_project(app)
    flow_names = {flow.name for flow in project.program.flows}
    record_names = {record.name for record in project.program.records}
    assert "inventory.calc_total" in flow_names
    assert "inventory.Product" in record_names


def test_unexported_symbol_is_blocked(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        'use "inventory" as inv\n'
        'page "home":\n'
        '  button "Calc":\n'
        '    calls flow "inv.internal"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    flow "public"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'flow "public":\n'
        "  return 5\n\n"
        'flow "internal":\n'
        "  return 10\n",
    )
    with pytest.raises(Namel3ssError) as excinfo:
        load_project(app)
    assert "does not export" in str(excinfo.value).lower()


def test_module_cycle_detection(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(app, 'use "alpha" as a\nflow "demo":\n  return "ok"\n')
    _write(
        tmp_path / "modules" / "alpha" / "capsule.ai",
        'capsule "alpha":\n'
        "  exports:\n"
        '    flow "one"\n',
    )
    _write(
        tmp_path / "modules" / "alpha" / "alpha.ai",
        'use "beta" as b\n'
        'flow "one":\n'
        "  return 1\n",
    )
    _write(
        tmp_path / "modules" / "beta" / "capsule.ai",
        'capsule "beta":\n'
        "  exports:\n"
        '    flow "two"\n',
    )
    _write(
        tmp_path / "modules" / "beta" / "beta.ai",
        'use "alpha" as a\n'
        'flow "two":\n'
        "  return 2\n",
    )
    with pytest.raises(Namel3ssError) as excinfo:
        load_project(app)
    assert "cycle" in str(excinfo.value).lower()


def test_package_fallback_for_modules(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        'use "inventory" as inv\n'
        'flow "demo":\n'
        '  return "ok"\n',
    )
    _write(
        tmp_path / "packages" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    flow "calc_total"\n',
    )
    _write(
        tmp_path / "packages" / "inventory" / "logic.ai",
        'flow "calc_total":\n'
        "  return 42\n",
    )
    project = load_project(app)
    flow_names = {flow.name for flow in project.program.flows}
    assert "inventory.calc_total" in flow_names
