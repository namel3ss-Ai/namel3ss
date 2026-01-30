from __future__ import annotations

import json
from pathlib import Path

from namel3ss.determinism import trace_hash
from namel3ss.observe import summarize_value
from namel3ss.observability.scrub import scrub_payload


def test_trace_hash_ignores_volatile_keys() -> None:
    traces_a = [
        {"type": "tool_call", "tool_name": "echo", "duration_ms": 5, "timestamp": "t1"},
    ]
    traces_b = [
        {"type": "tool_call", "tool_name": "echo", "duration_ms": 9, "timestamp": "t2"},
    ]
    assert trace_hash(traces_a) == trace_hash(traces_b)


def test_summarize_value_orders_keys() -> None:
    summary = summarize_value({"b": 1, "a": 2})
    assert summary.get("keys") == ["a", "b"]
    assert summary.get("count") == 2


def test_scrub_payload_redacts_secrets_and_paths(tmp_path: Path) -> None:
    secret = "sk-test-secret"
    path_value = str(tmp_path / "secret.txt")
    payload = {"token": secret, "path": path_value, "nested": {"path": path_value}}

    cleaned = scrub_payload(
        payload,
        secret_values=[secret],
        project_root=tmp_path,
        app_path=tmp_path / "app.ai",
    )

    blob = json.dumps(cleaned, sort_keys=True)
    assert secret not in blob
    assert path_value not in blob
    assert "***REDACTED***" in blob
    assert "<path>" in blob
