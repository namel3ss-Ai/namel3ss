from __future__ import annotations

from pathlib import Path

from namel3ss.observability.trace_runs import (
    latest_trace_run_id,
    list_trace_runs,
    read_trace_entries,
    write_trace_run,
)


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_trace_runs_write_list_and_read_are_deterministic(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    steps = [
        {
            "id": "step:0001",
            "kind": "flow_start",
            "what": 'flow "demo" started',
            "data": {"input": {"token": "secret", "value": 1}, "output": {"status": "ok"}},
            "line": 1,
            "column": 1,
        },
        {
            "id": "step:0002",
            "kind": "flow_end",
            "what": 'flow "demo" completed',
            "data": {"output": {"done": True}},
            "line": 2,
            "column": 1,
        },
    ]
    summary = write_trace_run(
        project_root=tmp_path,
        app_path=app,
        flow_name="demo",
        steps=steps,
        secret_values=["secret"],
    )
    assert summary is not None
    assert summary["run_id"] == "demo-000001"
    runs = list_trace_runs(tmp_path, app)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "demo-000001"
    assert latest_trace_run_id(tmp_path, app) == "demo-000001"

    entries = read_trace_entries(tmp_path, app, "demo-000001")
    assert len(entries) == 2
    assert entries[0]["step_id"] == "step:0001"
    assert entries[0]["timestamp"] == 1
    assert entries[0]["flow_name"] == "demo"
    assert entries[0]["input"]["token"] == "***REDACTED***"
    assert entries[1]["step_name"] == "flow_end"
