from __future__ import annotations

import os
from pathlib import Path

from namel3ss.cli.main import main as cli_main

TEMPLATES = [
    ("crud", "crud_app"),
    ("ai-assistant", "ai_app"),
    ("multi-agent", "multi_app"),
]


def _run(args: list[str], cwd: Path) -> int:
    prev = os.getcwd()
    os.chdir(cwd)
    try:
        return cli_main(args)
    finally:
        os.chdir(prev)


def test_templates_check_and_ui(tmp_path):
    for template, name in TEMPLATES:
        rc = _run(["new", template, name], tmp_path)
        assert rc == 0
        app_dir = tmp_path / name
        app_path = app_dir / "app.ai"
        assert app_path.exists()
        assert _run([str(app_path), "check"], tmp_path) == 0
        assert _run([str(app_path), "ui"], tmp_path) == 0
