from __future__ import annotations

import json

import namel3ss.cli.playground_mode as playground_mode
from namel3ss.cli.main import main as cli_main


SOURCE = 'spec is "1.0"\n\nflow "demo": purity is "pure"\n  return "ok"\n'


def test_playground_run_uses_default_timeout(monkeypatch, capsys) -> None:
    captured: dict[str, float] = {}

    def _fake_run(source: str, *, flow_name: str | None, input_payload: dict | None, timeout_seconds: float):
        _ = (source, flow_name, input_payload)
        captured["timeout_seconds"] = float(timeout_seconds)
        return {"ok": True, "flow_name": "demo", "result": "ok"}

    monkeypatch.setattr(playground_mode, "run_snippet", _fake_run)
    assert cli_main(["playground", "run", "--source", SOURCE, "--flow", "demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert captured["timeout_seconds"] == playground_mode.DEFAULT_PLAYGROUND_TIMEOUT_SECONDS


def test_playground_run_accepts_custom_timeout(monkeypatch, capsys) -> None:
    captured: dict[str, float] = {}

    def _fake_run(source: str, *, flow_name: str | None, input_payload: dict | None, timeout_seconds: float):
        _ = (source, flow_name, input_payload)
        captured["timeout_seconds"] = float(timeout_seconds)
        return {"ok": True, "flow_name": "demo", "result": "ok"}

    monkeypatch.setattr(playground_mode, "run_snippet", _fake_run)
    assert cli_main(
        ["playground", "run", "--source", SOURCE, "--flow", "demo", "--timeout", "7.5", "--json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert captured["timeout_seconds"] == 7.5

