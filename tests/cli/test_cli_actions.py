import json

from namel3ss.cli.main import main


SOURCE = '''spec is "1.0"

record "User":
  name string

flow "demo":
  return "ok"

page "home": requires true
  button "Run":
    calls flow "demo"
  form is "User"
'''


def test_actions_plain_text(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "actions"])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    action_lines = [line for line in out if line.startswith("page.")]
    assert action_lines[0].startswith("page.home.button.run  call_flow")
    assert action_lines[1].startswith("page.home.form.user  submit_form")
    assert action_lines == sorted(action_lines)


def test_actions_json(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "actions", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["count"] == len(payload["actions"])
    ids = [a["id"] for a in payload["actions"]]
    assert ids == sorted(ids)
    button = next(a for a in payload["actions"] if a["type"] == "call_flow")
    assert button["flow"] == "demo"
    form = next(a for a in payload["actions"] if a["type"] == "submit_form")
    assert form["record"] == "User"
