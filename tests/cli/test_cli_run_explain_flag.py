import json

from namel3ss.cli.main import main


SOURCE = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
  calc:
    total = sum(numbers)
  return total

page "home":
  button "Run":
    calls flow "demo"
'''


def test_run_explain_flag_prints_trace(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main(["run", str(path), "--explain"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Explain traces" in out


def test_run_without_explain_flag_is_unchanged(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert "Explain traces" not in out
