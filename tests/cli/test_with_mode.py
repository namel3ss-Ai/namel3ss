from pathlib import Path

from namel3ss.cli.with_mode import run_with_command


def test_with_mode_missing_pack(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    code = run_with_command([])
    captured = capsys.readouterr()
    assert code == 1
    assert "No tool report recorded yet" in captured.out
