import json

from namel3ss.cli.main import main


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def test_root_check_auto_detects_app(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["check"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "parse: ok" in out


def test_fmt_alias_with_file_first(tmp_path, capsys):
    path = _write_app(tmp_path)
    code = main([str(path), "fmt", "check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "ok" in out.lower()


def test_help_lists_new_short_commands(capsys):
    code = main(["help"])
    out = capsys.readouterr().out.lower()
    assert code == 0
    assert "pack" in out
    assert "ship" in out
    assert "where" in out
