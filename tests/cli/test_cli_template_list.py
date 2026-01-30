from pathlib import Path

from namel3ss.cli.main import main


def _expected_list() -> str:
    return (Path("tests") / "fixtures" / "cli" / "templates_list.txt").read_text(encoding="utf-8")


def test_template_list_command(capsys):
    code = main(["list"])
    out = capsys.readouterr().out
    assert code == 0
    assert out == _expected_list()