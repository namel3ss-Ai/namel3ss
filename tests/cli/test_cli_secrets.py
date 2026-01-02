import json
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.secrets import record_secret_access
from namel3ss.secrets.audit import AUDIT_FILENAME


APP_SOURCE = '''ai "assistant":
  provider is "openai"
  model is "gpt-4.1"

spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")


def test_secrets_status_reports_missing_and_available(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    code = main(["secrets", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    secret = payload["secrets"][0]
    assert secret["name"] == "NAMEL3SS_OPENAI_API_KEY"
    assert secret["available"] is False

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    code = main(["secrets", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    secret = payload["secrets"][0]
    assert secret["available"] is True
    assert secret["source"] == "env"

    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "sk-test")
    code = main(["secrets", "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    secret = payload["secrets"][0]
    assert secret["available"] is True
    assert secret["source"] == "env"


def test_secrets_audit_reports_access(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    audit_path = tmp_path / "secret_audit.jsonl"
    monkeypatch.setenv("N3_SECRET_AUDIT_PATH", str(audit_path))
    record_secret_access("NAMEL3SS_OPENAI_API_KEY", caller="test")
    code = main(["secrets", "audit", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["events"]


def test_secret_audit_path_override_avoids_repo_root(tmp_path, monkeypatch):
    audit_path = tmp_path / "secret_audit.jsonl"
    monkeypatch.setenv("N3_SECRET_AUDIT_PATH", str(audit_path))
    root_path = Path.cwd() / AUDIT_FILENAME
    pre_exists = root_path.exists()
    record_secret_access("NAMEL3SS_OPENAI_API_KEY", caller="test", project_root=tmp_path)
    assert audit_path.exists()
    if not pre_exists:
        assert not root_path.exists()
