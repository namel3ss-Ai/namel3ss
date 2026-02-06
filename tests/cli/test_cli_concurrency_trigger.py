from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'define function "calc":\n'
        "  input:\n"
        "    value is number\n"
        "  output:\n"
        "    total is number\n"
        "  return map:\n"
        '    "total" is value + 1\n\n'
        'flow "demo":\n'
        '  let task is async call function "calc":\n'
        "    value is 2\n"
        "  await task\n"
        "  return task.total\n",
        encoding="utf-8",
    )
    return app


def test_cli_concurrency_and_trigger_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["concurrency", "check", "--json"]) == 0
    concurrency_payload = json.loads(capsys.readouterr().out)
    assert concurrency_payload["ok"] is True

    assert cli_main(["trigger", "register", "webhook", "user_signup", "/hooks/signup", "demo", "--json"]) == 0
    register_payload = json.loads(capsys.readouterr().out)
    assert register_payload["ok"] is True
    assert register_payload["action"] == "register"

    assert cli_main(["trigger", "list", "--json"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["count"] == 1
    assert list_payload["items"][0]["name"] == "user_signup"


def test_cli_concurrency_reports_failures(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'flow "bad":\n'
        "  await missing\n"
        "  parallel:\n"
        '    run "one":\n'
        "      set state.total is 1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert cli_main(["concurrency", "check", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert int(payload["count"]) >= 2
