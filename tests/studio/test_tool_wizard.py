from __future__ import annotations

from pathlib import Path

from namel3ss.studio.tool_wizard import run_tool_wizard


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "tool_wizard"


def test_tool_wizard_generates_files(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    payload = {
        "tool_name": "greeter",
        "purity": "pure",
        "timeout_seconds": 12,
        "input_fields": "name:text\nage?:number\n",
        "output_fields": "message:text\nok:boolean\n",
    }
    result = run_tool_wizard(app_path, payload)
    assert result["ok"] is True
    tool_path = tmp_path / "tools" / "greeter.py"
    bindings_path = tmp_path / ".namel3ss" / "tools.yaml"
    expected_tool = (FIXTURES / "expected_tool.py").read_text(encoding="utf-8")
    expected_app = (FIXTURES / "expected_app.ai").read_text(encoding="utf-8")
    expected_bindings = (FIXTURES / "expected_tools.yaml").read_text(encoding="utf-8")
    assert tool_path.read_text(encoding="utf-8") == expected_tool
    assert app_path.read_text(encoding="utf-8") == expected_app
    assert bindings_path.read_text(encoding="utf-8") == expected_bindings


def test_tool_wizard_conflict_does_not_overwrite(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    tool_path = tools_dir / "greeter.py"
    tool_path.write_text("# existing\n", encoding="utf-8")
    payload = {
        "tool_name": "greeter",
        "purity": "impure",
        "input_fields": "",
        "output_fields": "",
    }
    result = run_tool_wizard(app_path, payload)
    assert result["ok"] is False
    assert result["status"] == "conflict"
    assert "suggested" in result
    assert tool_path.read_text(encoding="utf-8") == "# existing\n"


def test_tool_wizard_preview_does_not_write_files(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    payload = {
        "tool_name": "greeter",
        "purity": "pure",
        "input_fields": "name:text\n",
        "output_fields": "message:text\n",
        "preview": True,
    }
    result = run_tool_wizard(app_path, payload)
    assert result["ok"] is True
    assert result["status"] == "preview"
    preview = result["preview"]
    assert "tool_block" in preview
    assert "binding" in preview
    assert "stub" in preview
    assert not (tmp_path / ".namel3ss" / "tools.yaml").exists()
