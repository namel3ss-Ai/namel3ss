from __future__ import annotations

import json
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.runtime.audit.recorder import audit_schema
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.studio import data_api


def test_data_summary_and_audit_redaction(tmp_path: Path, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")

    db_path = (tmp_path / "data.db").as_posix()
    (tmp_path / "namel3ss.toml").write_text(
        "\n".join([
            "[persistence]",
            "target = \"sqlite\"",
            f"db_path = \"{db_path}\"",
        ]),
        encoding="utf-8",
    )

    secret = "audit-secret"
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", secret)

    config = load_config(app_path=app_path, root=tmp_path)
    store = resolve_store(config=config)
    schema = audit_schema()
    store.save(
        schema,
        {
            "flow": "demo",
            "action": "create",
            "timestamp": 10.0,
            "before": {"token": secret, "value": secret},
            "after": {},
        },
    )
    store.commit()

    summary = data_api.get_data_summary_payload(str(app_path))
    assert summary["schema_version"] == 1
    assert summary["persistence"]["target"] == "sqlite"

    payload = data_api.get_audit_payload(str(app_path), since=None, limit=10, filter_text="flow:demo")
    assert payload["schema_version"] == 1
    assert payload["events"], "expected audit events"
    blob = json.dumps(payload, default=str)
    assert secret not in blob

    empty = data_api.get_audit_payload(str(app_path), since=None, limit=10, filter_text="flow:missing")
    assert empty["events"] == []
