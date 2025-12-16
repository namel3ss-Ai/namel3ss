from namel3ss.cli.main import main


def test_help_command(tmp_path, capsys):
    code = main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Usage:" in out


def test_help_after_file(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    code = main([str(path), "help"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Usage:" in out
