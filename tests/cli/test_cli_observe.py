import json

from namel3ss.cli.main import main


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")


def test_observe_emits_events(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["run"])
    capsys.readouterr()
    code = main(["observe", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema_version"] == 1
    assert any(event.get("type") == "flow_run" for event in payload["events"])
