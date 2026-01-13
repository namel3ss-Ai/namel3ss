import json
from pathlib import Path

from namel3ss.cli.main import main


def _write_minimal_app(root: Path) -> None:
    (root / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")


def test_status_reports_missing_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_minimal_app(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = main(["status"])

    out = capsys.readouterr().out
    assert code == 0
    assert "No runtime artifacts found." in out


def test_status_reports_present_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_minimal_app(tmp_path)
    artifacts = tmp_path / ".namel3ss" / "outcome"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "last.json").write_text(
        json.dumps({"outcome": {"status": "ok"}}, indent=2), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    code = main(["status"])

    out = capsys.readouterr().out
    assert code == 0
    assert "Last run: success" in out
    assert "Artifacts present: yes" in out
    assert "Size:" in out
    assert ".namel3ss" in out
    assert "unknown time" not in out


def test_clean_is_interactive_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_minimal_app(tmp_path)
    artifacts = tmp_path / ".namel3ss"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "data.db").write_text("data", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    code = main(["clean"])

    out = capsys.readouterr().out
    assert code == 0
    assert artifacts.exists()
    assert "This will remove the namel3ss runtime artifacts:" in out
    assert "Aborted." in out


def test_clean_yes_removes_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_minimal_app(tmp_path)
    artifacts = tmp_path / ".namel3ss"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "trace.txt").write_text("details", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    code = main(["clean", "--yes"])

    out = capsys.readouterr().out
    assert code == 0
    assert not artifacts.exists()
    assert "Removed namel3ss runtime artifacts." in out
