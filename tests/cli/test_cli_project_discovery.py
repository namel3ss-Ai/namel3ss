import json
from pathlib import Path

from namel3ss.cli.main import main


APP_SOURCE = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
TEST_SOURCE = (
    'test "ok flow":\n'
    '  run flow "demo" with input: {} as result\n'
    '  expect value is "ok"\n'
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_commands_resolve_app_from_nested_dir(tmp_path, monkeypatch, capsys):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    _write(tmp_path / "tests" / "smoke_test.ai", TEST_SOURCE)
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    code = main(["run", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True

    code = main(["lint"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True

    code = main(["fmt", "check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "OK" in out

    code = main(["test", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["status"] == "ok"


def test_studio_dry_run_from_nested_dir(tmp_path, monkeypatch, capsys):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    code = main(["studio", "--dry"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Studio: http://127.0.0.1:" in out


def test_project_overrides_app_and_project(tmp_path, monkeypatch, capsys):
    root = tmp_path / "project"
    root.mkdir()
    app_path = root / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    _write(root / "tests" / "smoke_test.ai", TEST_SOURCE)
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)

    code = main(["run", "--app", str(app_path), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True

    code = main(["test", "--project", str(root), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["status"] == "ok"
