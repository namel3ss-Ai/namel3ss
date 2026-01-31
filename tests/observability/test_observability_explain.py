from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.explain_mode import build_explain_payload
from namel3ss.module_loader import load_project
from namel3ss.runtime.executor import execute_program_flow


def _build_source(secret_value: str, path_value: str) -> str:
    return f'''spec is "1.0"

flow "demo":
  log info "Starting" with map:
    "token" is "{secret_value}"
    "path" is "{path_value}"
  metric counter "requests" increment
  metric timing "render" record 5
  return "ok"
'''


def _run_app(tmp_path: Path, secret_value: str, path_value: str) -> Path:
    app_file = tmp_path / "app.ai"
    app_file.write_text(_build_source(secret_value, path_value), encoding="utf-8")
    project = load_project(app_file)
    execute_program_flow(project.program, "demo")
    return app_file


def test_explain_observability_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    secret_value = "sk-test-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret_value)
    monkeypatch.setenv("N3_OBSERVABILITY", "1")
    path_value = (tmp_path / "secrets.txt").as_posix()
    app_file = _run_app(tmp_path, secret_value, path_value)

    payload = build_explain_payload(app_file, include_observability=True)
    observability = payload.get("observability")
    assert isinstance(observability, dict)
    assert observability.get("logs")
    assert observability.get("spans")
    metrics = observability.get("metrics")
    assert isinstance(metrics, dict)
    assert metrics.get("timings")

    blob = json.dumps(observability, sort_keys=True)
    assert secret_value not in blob
    assert path_value not in blob
    assert "/Users/" not in blob
    assert "/home/" not in blob
    assert "C:\\" not in blob

    _run_app(tmp_path, secret_value, path_value)
    payload_again = build_explain_payload(app_file, include_observability=True)
    assert payload_again.get("observability") == observability

    disabled = build_explain_payload(app_file, include_observability=False)
    assert "observability" not in disabled
