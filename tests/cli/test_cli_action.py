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
    code = main([str(path), "page.home.button.run", "{}", "--json"])
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
    expected = (
        "What happened: Invalid JSON payload.\n"
        "Why: JSON parsing failed at line 1, column 2: Expecting property name enclosed in double quotes.\n"
        "Fix: Ensure the payload is valid JSON with double-quoted keys/strings.\n"
        'Example: {"values":{"name":"Ada"}}'
    )
    assert err.strip() == expected


FORM_SOURCE = '''record "User":
  name string
  email string

page "home":
  form is "User"
'''


def test_form_action_accepts_canonical_payload(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(FORM_SOURCE, encoding="utf-8")
    code = main([str(path), "page.home.form.user", '{"values":{"name":"Ada","email":"ada@example.com"}}', "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["record"] == "User"


def test_form_action_accepts_flat_payload(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(FORM_SOURCE, encoding="utf-8")
    code = main([str(path), "page.home.form.user", '{"name":"Ada","email":"ada@example.com"}', "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["record"] == "User"
