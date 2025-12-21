import sys
from pathlib import Path

from namel3ss.cli.main import main


def test_check_command_passes(tmp_path, capsys):
    app = tmp_path / "app.ai"
    app.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    exit_code = main([str(app), "check"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Parse: OK" in captured.out
    assert "Lint: OK" in captured.out
    assert "Manifest: OK" in captured.out


def test_check_command_fails_on_parse_error(tmp_path, capsys):
    app = tmp_path / "bad.ai"
    app.write_text('flow "demo"\n  return "ok"\n', encoding="utf-8")
    exit_code = main([str(app), "check"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "Parse: FAIL" in captured.out
