from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_exists_reads_last_artifacts(tmp_path: Path, capsys, monkeypatch) -> None:
    contract_dir = tmp_path / ".namel3ss" / "contract"
    contract_dir.mkdir(parents=True)
    (contract_dir / "last.json").write_text("{}\n", encoding="utf-8")
    (contract_dir / "last.plain").write_text("plain output\n", encoding="utf-8")
    (contract_dir / "last.exists.txt").write_text("exists output\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["exists"])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.strip() == "plain output"


def test_exists_builds_artifacts_when_missing(tmp_path: Path, capsys, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = cli_main(["exists"])
    out = capsys.readouterr().out

    contract_dir = tmp_path / ".namel3ss" / "contract"
    assert rc == 0
    assert "namel3ss exists" in out
    assert (contract_dir / "last.json").exists()
    assert (contract_dir / "last.plain").exists()
    assert (contract_dir / "last.exists.txt").exists()


def test_exists_handles_missing_file(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["exists", "missing.ai"])
    out = capsys.readouterr().out

    assert rc != 0
    assert "Missing app file" in out
