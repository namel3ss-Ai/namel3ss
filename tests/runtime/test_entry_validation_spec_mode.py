from pathlib import Path

from namel3ss.runtime.tools.entry_validation import validate_python_tool_entry_exists


def test_entry_validation_skips_tools_in_executable_spec(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("N3_EXECUTABLE_SPEC", "1")
    assert not (tmp_path / "tools").exists()
    module_path, function_name = validate_python_tool_entry_exists(
        "tools.echo:run",
        "runner echo",
        app_root=tmp_path,
        line=None,
        column=None,
    )
    assert module_path == "tools.echo"
    assert function_name == "run"
