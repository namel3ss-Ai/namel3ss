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


def test_default_run_single_flow(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path)])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"] == "ok"
