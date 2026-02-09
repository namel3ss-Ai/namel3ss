from __future__ import annotations

import json

from namel3ss.cli.main import main


APP_SOURCE = '''
spec is "1.0"

flow "demo":
  return "ok"
'''.lstrip()


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def test_state_list_json(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["state", "list", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "keys" in payload
    assert "persistence_backend" in payload


def test_state_inspect_missing_key_returns_not_found(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["state", "inspect", "unknown.key", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["key"] == "unknown.key"


def test_state_export_json(tmp_path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["state", "export", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "state" in payload
    assert "items" in payload["state"]
