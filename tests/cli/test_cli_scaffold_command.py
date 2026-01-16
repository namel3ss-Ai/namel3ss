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


def test_new_starter_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "starter", "first_run"])
    out = capsys.readouterr().out
    project_dir = tmp_path / "first_run"
    assert code == 0
    assert project_dir.exists()
    assert "Created project" in out
    assert "Next step" in out
    _assert_bracketless(out)
    _validate_app_file(project_dir / "app.ai")
    app_text = (project_dir / "app.ai").read_text(encoding="utf-8")
    assert "template: starter@0.1.0" in app_text
    assert (project_dir / "media" / "welcome.svg").exists()
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in readme
    assert "{{TEMPLATE_NAME}}" not in readme
    assert "{{TEMPLATE_VERSION}}" not in readme
    assert "first_run" in readme


def test_init_alias_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["init", "starter", "boot_app"])
    out = capsys.readouterr().out
    project_dir = tmp_path / "boot_app"
    assert code == 0
    assert project_dir.exists()
    assert "Created project" in out


def test_new_demo_output_is_minimal(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "demo", "demo_app"])
    out = capsys.readouterr().out.strip().splitlines()
    project_dir = tmp_path / "demo_app"
    assert code == 0
    assert project_dir.exists()
    assert out == [
        f"Created project at {project_dir}",
        "Run: cd demo_app && n3 run",
    ]


def test_new_demo_defaults_to_mock(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("N3_DEMO_PROVIDER", raising=False)
    monkeypatch.delenv("N3_DEMO_MODEL", raising=False)
    code = main(["new", "demo", "demo_app"])
    project_dir = tmp_path / "demo_app"
    assert code == 0
    source = (project_dir / "app.ai").read_text(encoding="utf-8")
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert 'provider is "mock"' in source
    assert 'model is "mock-model"' in source
    assert "DEMO_PROVIDER" not in source
    assert "DEMO_MODEL" not in source
    assert "DEMO_SYSTEM_PROMPT" not in source
    assert (project_dir / ".env.example").exists()
    assert (project_dir / "media" / "welcome.svg").exists()
    assert "{{PROJECT_NAME}}" not in readme
    assert "{{TEMPLATE_NAME}}" not in readme
    assert "{{TEMPLATE_VERSION}}" not in readme
    assert "demo_app" in readme


def test_new_demo_openai_env_controls_provider_and_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("N3_DEMO_PROVIDER", "openai")
    monkeypatch.setenv("N3_DEMO_MODEL", "gpt-test-mini")
    code = main(["new", "demo", "demo_app"])
    project_dir = tmp_path / "demo_app"
    assert code == 0
    source = (project_dir / "app.ai").read_text(encoding="utf-8")
    assert 'provider is "openai"' in source
    assert 'model is "gpt-test-mini"' in source
    env_example = (project_dir / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=" in env_example
    assert "NAMEL3SS_OPENAI_API_KEY=" in env_example
    assert "N3_DEMO_MODEL=gpt-4o-mini" not in env_example


def test_new_example_scaffolds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = main(["new", "example", "notes_journey", "journey_app"])
    project_dir = tmp_path / "journey_app"
    assert code == 0
    assert project_dir.exists()
    _validate_app_file(project_dir / "app.ai")
    app_text = (project_dir / "app.ai").read_text(encoding="utf-8")
    assert "example: notes_journey@0.1.0" in app_text
    assert (project_dir / "media" / "welcome.svg").exists()
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    assert "{{PROJECT_NAME}}" not in readme
    assert "journey_app" in readme


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
    assert main(["new", "starter", "same_app"]) == 0
    monkeypatch.chdir(second)
    assert main(["new", "starter", "same_app"]) == 0
    first_snapshot = _snapshot_tree(first / "same_app")
    second_snapshot = _snapshot_tree(second / "same_app")
    assert first_snapshot == second_snapshot


def test_new_scaffold_check_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "starter", "check_app"]) == 0
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
    project_dir = tmp_path / "starter"
    project_dir.mkdir()
    sentinel = project_dir / "keep.txt"
    sentinel.write_text("do not remove", encoding="utf-8")
    code = main(["new", "starter", "starter"])
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
    for name in ["demo", "starter"]:
        assert name in out
    assert "starter v0.1.0" in out
    assert "Examples (read-only)" in out
    assert "notes_journey" in out
