from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main


def test_fix_missing_artifacts(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["fix"])
    out = capsys.readouterr().out
    assert rc != 0
    assert "No error recorded yet" in out


def test_fix_reads_plain(tmp_path: Path, monkeypatch, capsys) -> None:
    errors_dir = tmp_path / ".namel3ss" / "errors"
    errors_dir.mkdir(parents=True)
    (errors_dir / "last.json").write_text("{}\n", encoding="utf-8")
    (errors_dir / "last.plain").write_text("plain error\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["fix"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == "plain error"
