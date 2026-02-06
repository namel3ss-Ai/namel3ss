from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.observability.trace_runs import write_trace_run


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def _seed_trace(tmp_path: Path, app: Path) -> str:
    summary = write_trace_run(
        project_root=tmp_path,
        app_path=app,
        flow_name="demo",
        steps=[
            {"id": "step:0001", "kind": "flow_start", "what": "start", "data": {"input": {"a": 1}}},
            {"id": "step:0002", "kind": "flow_end", "what": "end", "data": {"output": {"ok": True}}},
        ],
    )
    assert summary is not None
    return str(summary["run_id"])


def test_cli_trace_and_debug_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    app = _write_app(tmp_path)
    run_id = _seed_trace(tmp_path, app)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["trace", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["runs"][0]["run_id"] == run_id

    assert cli_main(["trace", "show", run_id, "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["ok"] is True
    assert shown["run_id"] == run_id
    assert shown["count"] == 2

    assert cli_main(["debug", "pause", run_id, "--json"]) == 0
    paused = json.loads(capsys.readouterr().out)
    assert paused["ok"] is True
    assert paused["paused"] is True
    assert paused["current_step"] == 0

    assert cli_main(["debug", "step", run_id, "--json"]) == 0
    stepped = json.loads(capsys.readouterr().out)
    assert stepped["ok"] is True
    assert stepped["current_step"] == 1

    assert cli_main(["debug", "back", run_id, "--json"]) == 0
    back = json.loads(capsys.readouterr().out)
    assert back["ok"] is True
    assert back["current_step"] == 0

    assert cli_main(["debug", "replay", run_id, "--json"]) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay["ok"] is True
    assert replay["current_step"] == replay["total_steps"] == 2


def test_cli_observability_init_and_export_traces(tmp_path: Path, capsys, monkeypatch) -> None:
    app = _write_app(tmp_path)
    _seed_trace(tmp_path, app)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["observability", "init", "--json"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["ok"] is True
    config_path = Path(created["config_path"])
    assert config_path.exists()

    config_path.write_text(
        (
            "redaction_rules: {}\n"
            "otlp_config:\n"
            "  endpoint: \"http://example.test/v1/traces\"\n"
            "  auth: {}\n"
            "  batch_size: 2\n"
            "metrics_enabled: true\n"
            "max_trace_size: 2000\n"
        ),
        encoding="utf-8",
    )

    calls: list[bytes] = []

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b"ok"

    def _fake_urlopen(request, timeout=5):  # noqa: ANN001
        _ = timeout
        calls.append(bytes(request.data or b""))
        return _DummyResponse()

    monkeypatch.setattr("namel3ss.observability.otlp_exporter.urlopen", _fake_urlopen)

    assert cli_main(["export", "traces", "--json"]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["ok"] is True
    assert exported["exported_spans"] == 2
    assert exported["failed_batches"] == 0
    assert len(calls) == 1
