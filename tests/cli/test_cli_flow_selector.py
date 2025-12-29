import json

from namel3ss.cli.main import main


SOURCE = '''spec is "1.0"

flow "one":
  return "a"

flow "two":
  return "b"
'''


def test_default_run_requires_flow_name(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "Multiple flows found" in err


def test_flow_command_runs_selected(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "flow", "two", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["result"] == "b"
