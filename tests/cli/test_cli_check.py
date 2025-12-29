from namel3ss.cli.main import main


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_check_command(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "OK" in out
