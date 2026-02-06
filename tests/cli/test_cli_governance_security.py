from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.governance.rbac import generate_token


APP_SOURCE = '''spec is "1.0"

ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(APP_SOURCE, encoding="utf-8")
    return app


def test_cli_auth_user_commands_are_deterministic(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["auth", "add-user", "alice", "--role", "developer", "--json"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["ok"] is True
    assert added["user"]["username"] == "alice"
    assert added["user"]["token"] == generate_token("alice")

    assert cli_main(["auth", "assign-role", "alice", "admin", "--json"]) == 0
    updated = json.loads(capsys.readouterr().out)
    assert updated["ok"] is True
    assert sorted(updated["user"]["roles"]) == ["admin", "developer"]

    assert cli_main(["auth", "list-users", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["users"][0]["username"] == "alice"
    assert sorted(listed["users"][0]["roles"]) == ["admin", "developer"]

    users_yaml = tmp_path / ".namel3ss" / "users.yaml"
    assert users_yaml.exists()


def test_cli_secret_vault_add_get_list(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", home.as_posix())
    monkeypatch.chdir(tmp_path)

    assert cli_main(["secret", "add", "db_password", "supersecret", "--owner", "alice", "--json"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["ok"] is True
    assert added["secret"]["name"] == "db_password"

    vault_path = tmp_path / ".namel3ss" / "secrets.json"
    assert vault_path.exists()
    vault_raw = vault_path.read_text(encoding="utf-8")
    assert "supersecret" not in vault_raw

    assert cli_main(["secret", "get", "db_password", "--json"]) == 0
    fetched = json.loads(capsys.readouterr().out)
    assert fetched["ok"] is True
    assert fetched["value"] == "supersecret"

    assert cli_main(["secret", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["secrets"][0]["name"] == "db_password"


def test_cli_secret_remove_deletes_entry(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", home.as_posix())
    monkeypatch.chdir(tmp_path)

    assert cli_main(["secret", "add", "db_password", "supersecret", "--json"]) == 0
    _ = json.loads(capsys.readouterr().out)

    assert cli_main(["secret", "remove", "db_password", "--json"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["ok"] is True
    assert removed["removed"]["name"] == "db_password"

    assert cli_main(["secret", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["count"] == 0


def test_cli_security_check_requires_guards(tmp_path: Path, capsys, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        (
            'spec is "1.0"\n\n'
            'record "Task":\n'
            "  fields:\n"
            "    id is number must be present\n"
            "    title is text must be present\n\n"
            'flow "mutate":\n'
            "  set state.task with:\n"
            "    id is 1\n"
            '    title is "Draft"\n'
            '  create "Task" with state.task as created\n'
            '  return "ok"\n'
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert cli_main(["security", "check", "--json"]) == 1
    failing = json.loads(capsys.readouterr().out)
    assert failing["ok"] is False
    assert any(row["code"] == "requires.flow_missing" for row in failing["violations"])

    app_path.write_text(
        (
            'spec is "1.0"\n\n'
            'record "Task":\n'
            "  fields:\n"
            "    id is number must be present\n"
            "    title is text must be present\n\n"
            'flow "mutate" requires true:\n'
            "  set state.task with:\n"
            "    id is 1\n"
            '    title is "Draft"\n'
            '  create "Task" with state.task as created\n'
            '  return "ok"\n'
        ),
        encoding="utf-8",
    )
    assert cli_main(["security", "check", "--json"]) == 0
    passing = json.loads(capsys.readouterr().out)
    assert passing["ok"] is True
    assert passing["count"] == 0


def test_cli_policy_check_and_audit_filters(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", home.as_posix())
    monkeypatch.chdir(tmp_path)

    (tmp_path / "policies.yaml").write_text(
        (
            "naming_convention: snake_case\n"
            "disallowed_model_providers:\n"
            "  - openai\n"
            "max_token_count_per_request: 1000\n"
        ),
        encoding="utf-8",
    )

    assert cli_main(["policy", "check", "--json"]) == 1
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is False
    assert checked["count"] >= 1
    assert any(item["rule_id"] == "disallowed_model_provider" for item in checked["violations"])

    assert cli_main(["secret", "add", "db_password", "topsecret", "--json"]) == 0
    _ = json.loads(capsys.readouterr().out)

    assert cli_main(["audit", "list", "--json"]) == 0
    audit_all = json.loads(capsys.readouterr().out)
    assert audit_all["ok"] is True
    assert audit_all["count"] >= 1

    assert cli_main(["audit", "filter", "--action", "secret_add", "--json"]) == 0
    audit_filtered = json.loads(capsys.readouterr().out)
    assert audit_filtered["ok"] is True
    assert audit_filtered["count"] >= 1
    assert all(item["action"] == "secret_add" for item in audit_filtered["entries"])
