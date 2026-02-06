from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    module_path = Path("scripts/audit_codebase.py").resolve()
    spec = importlib.util.spec_from_file_location("audit_codebase", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _create_minimal_repo(root: Path) -> None:
    _write(
        root / "src" / "namel3ss" / "compiler" / "core.py",
        "from namel3ss.runtime import executor\n\n\ndef compile_core():\n    return 'ok'\n",
    )
    _write(
        root / "src" / "namel3ss" / "runtime" / "engine.py",
        "def run():\n    return 'ok'\n",
    )
    _write(
        root / "src" / "namel3ss" / "ui" / "manifest.py",
        "from namel3ss.runtime.engine import run\n\n\ndef render():\n    return run()\n",
    )
    _write(
        root / "tests" / "runtime" / "test_engine.py",
        "from namel3ss.runtime.engine import run\n\n\ndef test_run():\n    assert run() == 'ok'\n",
    )
    _write(root / "docs" / "quickstart.md", "# Quickstart\n")


def test_collect_module_entries_and_contract_fields(tmp_path: Path) -> None:
    module = _load_module()
    _create_minimal_repo(tmp_path)

    entries = module.collect_module_entries(tmp_path)
    by_path = {entry.path: entry for entry in entries}

    assert "src/namel3ss/compiler" in by_path
    assert "src/namel3ss/runtime" in by_path
    assert "src/namel3ss/ui" in by_path
    assert "tests/runtime" in by_path

    compiler_entry = by_path["src/namel3ss/compiler"]
    assert compiler_entry.layer == "compiler"
    assert compiler_entry.lines_of_code > 0

    ui_entry = by_path["src/namel3ss/ui"]
    assert ui_entry.layer == "UI"

    contract_payload = compiler_entry.contract_payload()
    assert set(contract_payload.keys()) == {
        "name",
        "path",
        "description",
        "layer",
        "lines_of_code",
    }


def test_report_is_deterministic_and_check_mode(tmp_path: Path) -> None:
    module = _load_module()
    _create_minimal_repo(tmp_path)

    first = module.build_audit_report(tmp_path)
    second = module.build_audit_report(tmp_path)
    assert first == second

    out_path = tmp_path / "docs" / "reports" / "code_audit.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(first, encoding="utf-8")

    rc = module.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            str(out_path),
            "--check",
        ]
    )
    assert rc == 0

    out_path.write_text(first + "\n", encoding="utf-8")
    rc = module.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            str(out_path),
            "--check",
        ]
    )
    assert rc == 1


def test_empty_roots_render_report(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "src" / "namel3ss").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)

    report = module.build_audit_report(tmp_path)
    assert "# Codebase Audit Report" in report
    assert "| name | path | description | layer | lines_of_code | dependencies |" in report


def test_missing_required_directory_fails(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "src" / "namel3ss").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)

    with pytest.raises(module.AuditFailure):
        module.build_audit_report(tmp_path)
