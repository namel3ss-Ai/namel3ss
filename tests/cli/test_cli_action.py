import json

from namel3ss.cli.main import main


SOURCE = '''record "Item":
  name string

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def test_action_call_flow(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "page.home.button.run", "{}"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"] is not None


def test_invalid_payload_errors(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "page.home.button.run", "{"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Invalid JSON payload" in err
