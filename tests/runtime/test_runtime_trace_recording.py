from __future__ import annotations

from pathlib import Path

from namel3ss.observability.trace_runs import list_trace_runs, read_trace_entries
from tests.conftest import run_flow


def test_runtime_records_trace_run_file(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  let x is 1\n  return "ok"\n', encoding="utf-8")
    source = app.read_text(encoding="utf-8")

    result = run_flow(
        source,
        flow_name="demo",
        project_root=tmp_path,
        app_path=app,
    )
    assert result.last_value == "ok"

    runs = list_trace_runs(tmp_path, app)
    assert runs
    run_id = str(runs[0]["run_id"])
    entries = read_trace_entries(tmp_path, app, run_id)
    assert entries
    assert entries[0]["step_name"] == "flow_start"
    assert entries[-1]["step_name"] == "flow_end"
