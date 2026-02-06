from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


APP_OK = '''spec is "1.0"

record "User" version "1.0":
  id number
  name text

flow "list_users":
  return "ok"

route "list_users_route":
  path is "/users"
  method is "GET"
  request:
    input_text is text
  response:
    result is text
  flow is "list_users"
'''


APP_MISMATCH = '''spec is "1.0"

flow "get_count":
  return "oops"

route "count":
  path is "/count"
  method is "GET"
  request:
    input_text is text
  response:
    count is number
  flow is "get_count"
'''


def test_cli_ast_type_schema_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_OK, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["ast", "dump", "--json"]) == 0
    ast_payload = json.loads(capsys.readouterr().out)
    assert ast_payload["ok"] is True
    assert ast_payload["schema"] == "cir.v1"
    assert ast_payload["representation_schema"] == "program_representation.v1"

    assert cli_main(["type", "check", "--json"]) == 0
    type_payload = json.loads(capsys.readouterr().out)
    assert type_payload["ok"] is True

    assert cli_main(["schema", "infer", "--json"]) == 0
    infer_payload = json.loads(capsys.readouterr().out)
    assert infer_payload["ok"] is True
    assert Path(infer_payload["output_path"]).exists()

    assert cli_main(["schema", "migrate", "--json"]) == 0
    migrate_payload = json.loads(capsys.readouterr().out)
    assert migrate_payload["ok"] is True
    assert Path(migrate_payload["output_path"]).exists()


def test_cli_type_check_reports_mismatch(tmp_path: Path, capsys, monkeypatch) -> None:
    app = tmp_path / "app.ai"
    app.write_text(APP_MISMATCH, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["type", "check", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    codes = {
        issue["code"]
        for issue in payload.get("issues", [])
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    }
    assert "type.route_response_mismatch" in codes
