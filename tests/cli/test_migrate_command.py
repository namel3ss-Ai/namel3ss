from __future__ import annotations

import json

from namel3ss.cli.main import main


APP_SOURCE = '''
record "Item":
  name text

spec is "1.0"

flow "demo":
  return "ok"
'''.lstrip()


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def test_migrate_status_json_payload(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "--status", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["target"] == "local"
    assert payload["state_schema_version"] == "state_schema@1"
    assert "migration_status" in payload
    assert "persistence_backend" in payload


def test_migrate_dry_run_json_payload(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "--dry-run", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["migration_status"]["schema_version"] == "migration_status@1"


def test_migrate_plan_still_delegates_legacy_subcommand(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "plan", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "plan" in payload
