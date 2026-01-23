from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.format import format_source
from namel3ss.ir.nodes import lower_program
from namel3ss.lint.engine import lint_source
from namel3ss.parser.core import parse


def _validate_app_file(app_path: Path) -> None:
    source = app_path.read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in source
    assert "{{TEMPLATE_NAME}}" not in source
    assert "{{TEMPLATE_VERSION}}" not in source
    assert format_source(source) == source
    findings = lint_source(source)
    assert len(findings) == 0
    ast_program = parse(source)
    lower_program(ast_program)


def _assert_bracketless(text: str) -> None:
    for ch in "[]{}()":
        assert ch not in text


def test_new_operations_dashboard_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "operations_dashboard", "first_run"])
    out = capsys.readouterr().out
    project_dir = tmp_path / "first_run"
    assert code == 0
    assert project_dir.exists()
    assert "Created project" in out
    assert "Next step" in out
    _assert_bracketless(out)
    _validate_app_file(project_dir / "app.ai")
    assert (project_dir / "expected_ui.json").exists()
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in readme
    assert "{{TEMPLATE_NAME}}" not in readme
    assert "{{TEMPLATE_VERSION}}" not in readme
    assert "first_run" in readme


def test_init_alias_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["init", "onboarding", "boot_app"])
    out = capsys.readouterr().out
    project_dir = tmp_path / "boot_app"
    assert code == 0
    assert project_dir.exists()
    assert "Created project" in out


def test_new_example_scaffolds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "example", "hello_flow", "hello_app"])
    project_dir = tmp_path / "hello_app"
    assert code == 0
    assert project_dir.exists()
    _validate_app_file(project_dir / "app.ai")
    app_text = (project_dir / "app.ai").read_text(encoding="utf-8")
    assert "example: hello_flow@0.1.0" in app_text
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in readme
    assert "hello_app" in readme


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def test_new_scaffold_is_deterministic(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.chdir(first)
    assert main(["new", "operations_dashboard", "same_app"]) == 0
    monkeypatch.chdir(second)
    assert main(["new", "operations_dashboard", "same_app"]) == 0
    first_snapshot = _snapshot_tree(first / "same_app")
    second_snapshot = _snapshot_tree(second / "same_app")
    assert first_snapshot == second_snapshot


def test_new_scaffold_check_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "operations_dashboard", "check_app"]) == 0
    app_path = tmp_path / "check_app" / "app.ai"
    assert main([str(app_path), "check"]) == 0


def test_new_unknown_template_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "unknown"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Unknown template" in captured.err
    assert list(tmp_path.iterdir()) == []


def test_new_existing_directory_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    project_dir = tmp_path / "operations_dashboard"
    project_dir.mkdir()
    sentinel = project_dir / "keep.txt"
    sentinel.write_text("do not remove", encoding="utf-8")
    code = main(["new", "operations_dashboard", "operations_dashboard"])
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
    for name in ["Operations Dashboard", "Onboarding", "Support Inbox"]:
        assert name in out
    assert "Examples (read-only)" in out
    assert "Hello Flow" in out
