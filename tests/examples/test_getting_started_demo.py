from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.tools.bindings import bindings_path
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, render_bindings_yaml
from namel3ss.utils.slugify import slugify_tool_name
from tests._ci_debug import debug_context


DEMO_ROOT = Path("examples/getting_started")


def _copy_demo(tmp_path: Path) -> Path:
    dest = tmp_path / "getting_started"
    shutil.copytree(DEMO_ROOT, dest)
    return dest


def _node_available() -> bool:
    return shutil.which("node") is not None


def _bind_tools(app_path: Path) -> int:
    app_root = app_path.parent
    bindings = {
        "format greeting": ToolBinding(
            kind="python",
            entry=f"tools.{slugify_tool_name('format greeting')}:run",
        ),
        "node greeting": ToolBinding(
            kind="node",
            entry=f"tools.{slugify_tool_name('node greeting')}:run",
            runner="node",
        ),
    }
    path = bindings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_bindings_yaml(bindings), encoding="utf-8")
    return 0


def test_getting_started_demo_check(tmp_path: Path, capsys) -> None:
    demo = _copy_demo(tmp_path)
    app_path = demo / "app.ai"
    assert _bind_tools(app_path) == 0
    code = cli_main([str(app_path), "check"])
    captured = capsys.readouterr()
    out = captured.out
    if code != 0 and os.getenv("CI") == "true":
        tools_dir = demo / "tools"
        tools_files = sorted(p.name for p in tools_dir.iterdir()) if tools_dir.exists() else []
        print(json.dumps(debug_context("getting_started_check", app_root=demo), sort_keys=True))
        print(json.dumps({"tools_dir": str(tools_dir), "files": tools_files}, sort_keys=True))
        print("stdout:\n" + captured.out)
        print("stderr:\n" + captured.err)
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
