from namel3ss.cli.main import main


SOURCE = 'spec is "1.0"\n\nflow "demo":\n    return "ok"\n'


def test_format_check_detects_changes(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "format", "check"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Needs formatting" in out


def test_format_rewrites_and_check_passes(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "format"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Formatted" in out or "Already formatted" in out

    code = main([str(path), "format", "check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "OK" in out
