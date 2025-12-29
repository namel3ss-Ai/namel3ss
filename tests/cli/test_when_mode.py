from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_when_missing_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["when"])
    out = capsys.readouterr().out
    assert rc != 0
    assert "Missing app.ai" in out


def test_when_reads_plain(tmp_path: Path, monkeypatch, capsys) -> None:
    spec_dir = tmp_path / ".namel3ss" / "spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "last.json").write_text("{}\n", encoding="utf-8")
    (spec_dir / "last.plain").write_text("spec output\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["when"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == "spec output"


def test_when_builds_from_app(tmp_path: Path, monkeypatch, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["when", "app.ai"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "spec check" in out.lower()
    spec_dir = tmp_path / ".namel3ss" / "spec"
    assert (spec_dir / "last.json").exists()
