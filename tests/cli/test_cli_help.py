from pathlib import Path

from namel3ss.cli.main import main


def _expected_help() -> str:
    return (Path("tests") / "golden" / "cli" / "help.txt").read_text(encoding="utf-8")


def test_help_command(tmp_path, capsys):
    code = main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    assert out == _expected_help()


def test_help_after_file(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    code = main([str(path), "help"])
    out = capsys.readouterr().out
    assert code == 0
    assert out == _expected_help()
