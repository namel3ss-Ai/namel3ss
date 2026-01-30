from __future__ import annotations

import json
from pathlib import Path

from namel3ss.beta_lock.repo_clean import repo_dirty_entries
from namel3ss.module_loader import load_project
from namel3ss.observability.log_store import read_logs
from namel3ss.observability.metrics_store import read_metrics
from namel3ss.observability.trace_store import read_spans
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.observability_api import (
    get_logs_payload,
    get_metrics_payload,
    get_trace_payload,
    get_traces_payload,
)


def _build_source(secret_value: str, path_value: str) -> str:
    return f'''spec is "1.0"

flow "demo":
  log info "Starting" with map:
    "token" is "{secret_value}"
    "path" is "{path_value}"
  log warn "Warning"
  metric counter "errors" set 3
  metric counter "requests" increment
  metric counter "requests" add 2 with map:
    "path" is "{path_value}"
    "token" is "{secret_value}"
  metric timing "render" record 5
  return "ok"
'''


def _run_app(tmp_path: Path, secret_value: str, path_value: str) -> Path:
    app_file = tmp_path / "app.ai"
    app_file.write_text(_build_source(secret_value, path_value), encoding="utf-8")
    project = load_project(app_file)
    execute_program_flow(project.program, "demo")
    return app_file


def _assert_scrubbed(payload: object, secret_value: str, path_value: str) -> None:
    blob = json.dumps(payload, sort_keys=True)
    assert secret_value not in blob
    assert path_value not in blob


def test_logs_metrics_spans_are_scrubbed_and_stable(tmp_path: Path, monkeypatch) -> None:
    secret_value = "sk-test-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)
    path_value = (tmp_path / "secrets.txt").as_posix()
    app_file = _run_app(tmp_path, secret_value, path_value)

    logs = read_logs(tmp_path, app_file)
    spans = read_spans(tmp_path, app_file)
    metrics = read_metrics(tmp_path, app_file)

    assert logs
    assert spans
    assert isinstance(metrics, dict)

    _assert_scrubbed(logs, secret_value, path_value)
    _assert_scrubbed(spans, secret_value, path_value)
    _assert_scrubbed(metrics, secret_value, path_value)

    assert logs[0].get("id") == "log:0001"
    assert logs[1].get("id") == "log:0002"
    assert logs[0].get("fields", {}).get("token") == "***REDACTED***"
    assert logs[0].get("fields", {}).get("path") == "<path>"
    assert all(isinstance(entry.get("order"), int) for entry in logs)
    run_events = [entry for entry in logs if entry.get("event_kind") == "run"]
    assert run_events
    assert run_events[-1].get("scope") == "runtime"
    log_ids = [entry.get("id") for entry in logs]
    assert log_ids == sorted(log_ids)

    assert spans[0].get("id") == "span:0001"
    assert spans[0].get("status") == "ok"
    span_ids = [entry.get("id") for entry in spans]
    assert span_ids == sorted(span_ids)

    counter_names = {entry.get("name") for entry in metrics.get("counters", [])}
    timing_names = {entry.get("name") for entry in metrics.get("timings", [])}
    assert "errors" in counter_names
    assert "requests" in counter_names
    assert "render" in timing_names

    labeled = [entry for entry in metrics.get("counters", []) if entry.get("labels")]
    assert labeled
    label_values = set(str(val) for entry in labeled for val in entry.get("labels", {}).values())
    assert "***REDACTED***" in label_values
    assert "<path>" in label_values
    counters = metrics.get("counters", [])
    timings = metrics.get("timings", [])
    assert counters == sorted(counters, key=_metric_sort_key)
    assert timings == sorted(timings, key=_metric_sort_key)

    _run_app(tmp_path, secret_value, path_value)
    logs_again = read_logs(tmp_path, app_file)
    spans_again = read_spans(tmp_path, app_file)
    metrics_again = read_metrics(tmp_path, app_file)
    assert logs == logs_again
    assert spans == spans_again
    assert metrics == metrics_again


def test_observability_endpoints_payloads(tmp_path: Path, monkeypatch) -> None:
    secret_value = "sk-test-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)
    path_value = (tmp_path / "secrets.txt").as_posix()
    app_file = _run_app(tmp_path, secret_value, path_value)

    logs_payload = get_logs_payload(tmp_path, app_file)
    trace_payload = get_trace_payload(tmp_path, app_file)
    traces_payload = get_traces_payload(tmp_path, app_file)
    metrics_payload = get_metrics_payload(tmp_path, app_file)

    assert logs_payload.get("ok") is True
    assert trace_payload.get("ok") is True
    assert traces_payload.get("ok") is True
    assert metrics_payload.get("ok") is True
    assert logs_payload.get("count") == len(logs_payload.get("logs", []))
    assert trace_payload.get("count") == len(trace_payload.get("spans", []))
    assert traces_payload.get("count") == len(traces_payload.get("spans", []))
    assert isinstance(metrics_payload.get("counters"), list)
    assert isinstance(metrics_payload.get("timings"), list)
    assert trace_payload == traces_payload
    summary = metrics_payload.get("summary")
    assert isinstance(summary, dict)
    expected = json.loads(Path("tests/fixtures/observability_summary.json").read_text(encoding="utf-8"))
    assert summary == expected

    _assert_scrubbed(logs_payload, secret_value, path_value)
    _assert_scrubbed(trace_payload, secret_value, path_value)
    _assert_scrubbed(traces_payload, secret_value, path_value)
    _assert_scrubbed(metrics_payload, secret_value, path_value)


def test_observability_repo_clean(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[2]
    baseline = set(repo_dirty_entries(root))
    secret_value = "sk-test-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)
    path_value = (tmp_path / "secrets.txt").as_posix()
    _run_app(tmp_path, secret_value, path_value)
    dirty = set(repo_dirty_entries(root))
    assert dirty == baseline


def _metric_sort_key(entry: dict) -> tuple:
    name = str(entry.get("name", ""))
    labels = entry.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}
    label_key = tuple((str(key), str(labels.get(key))) for key in sorted(labels.keys(), key=lambda item: str(item)))
    return (name, label_key)
