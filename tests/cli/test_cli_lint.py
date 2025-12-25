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


def test_cli_lint_tool_warnings_do_not_fail_without_strict(tmp_path, capsys):
    source = '''tool "get data":
  implemented using python

  input:
    url is text

  output:
    data is json

flow "demo":
  return "ok"
'''
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")
    code = main([str(path), "lint", "check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert any(f["code"] == "tools.missing_binding" for f in payload["findings"])


def test_cli_lint_strict_tools_fails_on_tool_warnings(tmp_path, capsys):
    source = '''tool "get data":
  implemented using python

  input:
    url is text

  output:
    data is json

flow "demo":
  return "ok"
'''
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")
    code = main([str(path), "lint", "check", "--strict-tools"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert any(f["code"] == "tools.missing_binding" for f in payload["findings"])


def test_cli_lint_fails_on_tool_collision(tmp_path, capsys):
    source = '''tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

flow "demo":
  return "ok"
'''
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "slugify text":\n    kind: "python"\n    entry: "tools.custom:run"\n',
        encoding="utf-8",
    )
    code = main([str(path), "lint", "check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert any(f["code"] == "tools.collision" for f in payload["findings"])


def test_cli_lint_fails_on_invalid_runner(tmp_path, capsys):
    source = '''tool "get data":
  implemented using python

  input:
    url is text

  output:
    data is json

flow "demo":
  return "ok"
'''
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "get data":\n    kind: "python"\n    entry: "tools.http:run"\n    runner: "bogus"\n',
        encoding="utf-8",
    )
    code = main([str(path), "lint", "check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert any(f["code"] == "tools.invalid_runner" for f in payload["findings"])
