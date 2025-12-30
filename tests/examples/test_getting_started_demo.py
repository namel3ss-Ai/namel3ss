from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from namel3ss.cli.main import main as cli_main


DEMO_ROOT = Path("examples/getting_started")


def _copy_demo(tmp_path: Path) -> Path:
    dest = tmp_path / "getting_started"
    shutil.copytree(DEMO_ROOT, dest)
    return dest


def _node_available() -> bool:
    return shutil.which("node") is not None


def test_getting_started_demo_check(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    code = cli_main([str(app_path), "check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Parse: OK" in out
    assert "Lint: OK" in out
    assert "Manifest: OK" in out


def test_getting_started_demo_ui_export(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    code = cli_main([str(app_path), "ui", "export"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    export_dir = Path(payload["export_dir"])
    assert export_dir.exists()
    assert (export_dir / "ui.json").exists()
    assert (export_dir / "actions.json").exists()
    assert (export_dir / "schema.json").exists()


def test_getting_started_demo_python_flow(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    code = cli_main([str(app_path), "flow", "python_demo", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"]["message"] == "Hello Ada"


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_getting_started_demo_node_flow(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    code = cli_main([str(app_path), "flow", "node_demo", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"]["message"] == "Hello Ada"


def test_getting_started_demo_ai_flow(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    code = cli_main([str(app_path), "flow", "ai_demo", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"] is not None
