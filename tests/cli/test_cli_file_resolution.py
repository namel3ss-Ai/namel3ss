import json

from namel3ss.cli.main import main


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def test_run_defaults_to_app_in_cwd(tmp_path, capsys, monkeypatch):
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    code = main(["run", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["result"] == "ok"


def test_run_without_app_ai_fails_cleanly(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code = main(["run"])
    captured = capsys.readouterr()

    assert code != 0
    assert "No app.ai found. Run `n3 run <file.ai>` or create app.ai." in captured.err
