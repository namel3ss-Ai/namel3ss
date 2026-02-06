from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.runtime.security.retention_enforcer import enforce_retention_policies


def _set_mtime(path: Path, timestamp: float) -> None:
    os.utime(path, (timestamp, timestamp))


def test_retention_purge_removes_expired_persisted_files(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            "  enabled: true\n"
            '  algorithm: "aes-256-gcm"\n'
            "  key: env:N3_ENCRYPTION_KEY\n"
            "resource_limits:\n"
            "  max_memory_mb: 64\n"
            "  max_cpu_ms: 5000\n"
            "retention:\n"
            "  traces: 1\n"
            "  models: 1\n"
            "  feedback: 1\n"
        ),
        encoding="utf-8",
    )

    now_epoch = 1_800_000_000.0
    old_epoch = now_epoch - (3 * 86400)
    traces_root = tmp_path / ".namel3ss" / "traces"
    traces_root.mkdir(parents=True, exist_ok=True)
    trace_file = traces_root / "demo-000001.jsonl"
    trace_file.write_text('{"step_id":"demo:step:0001","timestamp":1}\n', encoding="utf-8")
    (traces_root / "index.json").write_text(
        json.dumps({"schema_version": 1, "next_counter": 2, "latest_run_id": "demo-000001", "runs": [{"run_id": "demo-000001", "sequence": 1}]}),
        encoding="utf-8",
    )
    feedback_file = tmp_path / ".namel3ss" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_file.write_text('{"flow_name":"demo","input_id":"1","rating":"good","step_count":1}\n', encoding="utf-8")
    mlops_snapshot = tmp_path / ".namel3ss" / "mlops_registry.json"
    mlops_snapshot.write_text('{"models":[]}', encoding="utf-8")
    _set_mtime(trace_file, old_epoch)
    _set_mtime(feedback_file, old_epoch)
    _set_mtime(mlops_snapshot, old_epoch)

    payload = enforce_retention_policies(tmp_path, app_path, now_epoch_seconds=now_epoch)
    removed = set(payload["removed"])
    assert trace_file.as_posix() in removed
    assert feedback_file.as_posix() in removed
    assert mlops_snapshot.as_posix() in removed
    assert not trace_file.exists()
    assert not feedback_file.exists()
    assert not mlops_snapshot.exists()


def test_retention_anonymization_redacts_configured_fields(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            "  enabled: true\n"
            '  algorithm: "aes-256-gcm"\n'
            "  key: env:N3_ENCRYPTION_KEY\n"
            "resource_limits:\n"
            "  max_memory_mb: 64\n"
            "  max_cpu_ms: 5000\n"
            "retention:\n"
            "  feedback: 99999\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "retention.yaml").write_text(
        (
            'version: "1.0"\n'
            "records:\n"
            "  orders:\n"
            "    retention_days: 30\n"
            "    anonymize_fields:\n"
            "      - customer_email\n"
            "audit:\n"
            "  enabled: true\n"
            "  retention_days: 30\n"
        ),
        encoding="utf-8",
    )
    feedback_file = tmp_path / ".namel3ss" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_file.write_text(
        '{"flow_name":"demo","input_id":"1","rating":"good","step_count":1,"customer_email":"a@example.com"}\n',
        encoding="utf-8",
    )

    payload = enforce_retention_policies(tmp_path, app_path, now_epoch_seconds=1_800_000_000.0)
    assert feedback_file.as_posix() in set(payload["redacted"])
    line = feedback_file.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["customer_email"] == "[REDACTED]"
