from __future__ import annotations

import json
from pathlib import Path

from namel3ss.studio import trust_api


def test_trust_payloads_and_redaction(tmp_path: Path, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")

    secret = "supersecret-value"
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", secret)

    observe_path = tmp_path / ".namel3ss" / "observe.jsonl"
    observe_path.parent.mkdir(parents=True, exist_ok=True)
    observe_path.write_text(
        json.dumps({"type": "audit", "detail": f"token {secret}", "time": 10.0}) + "\n",
        encoding="utf-8",
    )

    summary = trust_api.get_trust_summary_payload(str(app_path))
    assert summary["schema_version"] == 1
    assert "engine_target" in summary

    proof = trust_api.get_trust_proof_payload(str(app_path))
    assert proof["schema_version"] == 1
    assert proof.get("ok") is False

    observe = trust_api.get_trust_observe_payload(str(app_path), since=None, limit=10)
    assert observe["schema_version"] == 1
    assert secret not in json.dumps(observe)

    explain = trust_api.get_trust_explain_payload(str(app_path))
    assert explain["schema_version"] == 1

    verify = trust_api.apply_trust_verify(str(app_path), {"prod": False})
    assert verify["schema_version"] == 1
