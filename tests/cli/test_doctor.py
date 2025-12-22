from __future__ import annotations

import json
import os

from namel3ss.cli.main import main as cli_main


def test_doctor_plain_output(capsys):
    rc = cli_main(["doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Python" in out
    assert "Studio assets" in out or "Studio" in out


def test_doctor_json_contains_keys(monkeypatch, capsys):
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "secret-value")
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert "version" in data
    assert "python" in data and "supported" in data["python"]
    assert data["providers"]["NAMEL3SS_OPENAI_API_KEY"] == "present"
    # ensure secret value not present in output
    assert "secret-value" not in out
    assert data["studio"]["assets_present"] is True
