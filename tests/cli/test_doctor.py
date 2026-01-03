from __future__ import annotations

import json
import os

from namel3ss.cli.main import main as cli_main


def test_doctor_plain_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.ai").write_text("", encoding="utf-8")
    rc = cli_main(["doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Environment:" in out
    assert "Project:" in out
    assert "AI providers:" in out
    assert "Fix:" in out


def test_doctor_json_contains_keys(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.ai").write_text("", encoding="utf-8")
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "secret-value")
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    checks = {c["id"]: c for c in data["checks"]}
    assert data["status"] in {"ok", "warning", "error"}
    assert checks["python_version"]["status"] in {"ok", "error"}
    assert checks["provider_envs"]["status"] == "warning"
    # ensure secret value not present in output
    assert "secret-value" not in out


def test_doctor_json_is_deterministic(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    out_first = capsys.readouterr().out
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    out_second = capsys.readouterr().out
    assert out_first == out_second


def test_doctor_warns_on_missing_provider_keys(monkeypatch, tmp_path, capsys):
    app_source = (
        'ai "assistant":\n'
        '  provider is "openai"\n'
        '  model is "gpt-4o-mini"\n'
        '\n'
        'spec is "1.0"\n'
        '\n'
        'flow "demo":\n'
        '  return "ok"\n'
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.ai").write_text(app_source, encoding="utf-8")
    monkeypatch.delenv("NAMEL3SS_OPENAI_API_KEY", raising=False)
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    provider_check = checks["provider_envs"]
    assert provider_check["status"] == "warning"
    assert "NAMEL3SS_OPENAI_API_KEY" in provider_check["message"]
