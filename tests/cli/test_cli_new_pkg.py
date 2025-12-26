from __future__ import annotations

import os
from pathlib import Path

from namel3ss.cli.main import main


def test_cli_new_pkg_scaffold(tmp_path):
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["new", "pkg", "demo_pkg"]) == 0
    finally:
        os.chdir(prev)
    root = tmp_path / "demo_pkg"
    assert (root / "capsule.ai").exists()
    assert (root / "modules" / "demo_pkg" / "capsule.ai").exists()
    assert (root / "modules" / "demo_pkg" / "logic.ai").exists()
    assert (root / "README.md").exists()
    assert (root / "LICENSE").exists()
    assert (root / "namel3ss.package.json").exists()
    assert (root / "checksums.json").exists()
    assert (root / "namel3ss.toml").exists()
    assert (root / "tests" / "demo_pkg_test.ai").exists()
    assert (root / "app.ai").exists()
    assert (root / "docs" / "README.md").exists()
