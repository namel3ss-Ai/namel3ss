import json
import os
from pathlib import Path

from namel3ss.cli.main import main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cli_test_runner_json(tmp_path, capsys):
    app = tmp_path / "app.ai"
    _write(
        app,
        'spec is "1.0"\n\n'
        'use "inventory" as inv\n'
        'flow "ok":\n'
        '  return "ok"\n'
        'flow "bad":\n'
        "  return missing\n",
    )
    _write(
        tmp_path / "modules" / "inventory" / "capsule.ai",
        'capsule "inventory":\n'
        "  exports:\n"
        '    flow "calc_total"\n',
    )
    _write(
        tmp_path / "modules" / "inventory" / "logic.ai",
        'flow "calc_total":\n'
        "  return 5\n",
    )
    _write(
        tmp_path / "tests" / "smoke_test.ai",
        'use "inventory" as inv\n'
        '\n'
        'test "ok flow":\n'
        "  run flow \"ok\" with input: {} as result\n"
        "  expect value is \"ok\"\n"
        '\n'
        'test "module flow":\n'
        "  run flow \"inv.calc_total\" with input: {} as result\n"
        "  expect value is 5\n"
        '\n'
        'test "error flow":\n'
        "  run flow \"bad\" with input: {} as result\n"
        "  expect error contains \"Unknown variable\"\n",
    )
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        code = main(["test", "--json"])
    finally:
        os.chdir(prev)
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["status"] == "ok"
    assert len(payload["tests"]) == 3
