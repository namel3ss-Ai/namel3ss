from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.format import format_source
from namel3ss.ir.nodes import lower_program
from namel3ss.lint.engine import lint_source
from namel3ss.parser.core import parse


def _validate_app_file(app_path: Path) -> None:
    source = app_path.read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in source
    assert format_source(source) == source
    findings = lint_source(source)
    assert len(findings) == 0
    ast_program = parse(source)
    lower_program(ast_program)


def test_new_crud_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "crud", "my_app"])
    out = capsys.readouterr().out
    project_dir = tmp_path / "my_app"
    assert code == 0
    assert project_dir.exists()
    assert "Created project" in out
    _validate_app_file(project_dir / "app.ai")
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in readme
    assert "my_app" in readme


def test_new_ai_assistant_defaults_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "ai-assistant"])
    project_dir = tmp_path / "ai_assistant"
    assert code == 0
    assert project_dir.exists()
    _validate_app_file(project_dir / "app.ai")
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "ai_assistant" in readme


def test_new_unknown_template_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "unknown"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Unknown template" in captured.err
    assert list(tmp_path.iterdir()) == []


def test_new_existing_directory_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    project_dir = tmp_path / "crud"
    project_dir.mkdir()
    sentinel = project_dir / "keep.txt"
    sentinel.write_text("do not remove", encoding="utf-8")
    code = main(["new", "crud", "crud"])
    captured = capsys.readouterr()
    assert code == 1
    assert "already exists" in captured.err
    assert sentinel.read_text(encoding="utf-8") == "do not remove"
    assert not (project_dir / "app.ai").exists()


def test_new_lists_templates(capsys):
    code = main(["new"])
    captured = capsys.readouterr()
    assert code == 0
    out = captured.out
    assert "Available templates" in out
    for name in ["crud", "ai-assistant", "multi-agent"]:
        assert name in out
