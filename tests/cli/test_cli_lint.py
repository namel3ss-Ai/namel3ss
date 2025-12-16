import json

from namel3ss.cli.main import main


GOOD = 'flow "demo":\n  return "ok"\n'
BAD = 'flow is "demo"\n'


def test_cli_lint_outputs_json(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(BAD, encoding="utf-8")
    code = main([str(path), "lint"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["count"] >= 1


def test_cli_lint_check_fails_on_findings(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(BAD, encoding="utf-8")
    code = main([str(path), "lint", "check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["count"] >= 1


def test_cli_lint_check_passes_when_clean(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(GOOD, encoding="utf-8")
    code = main([str(path), "lint", "check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["count"] == 0
