from __future__ import annotations

from copy import deepcopy

from namel3ss.runtime.audit.replay_engine import replay_run_artifact
from namel3ss.runtime.audit.run_artifact import build_run_artifact


def _response_with_capability_trace() -> dict:
    return {
        "ok": True,
        "state": {},
        "result": {"answer": "ok"},
        "traces": [
            {
                "type": "capability_check",
                "tool_name": "get json from web",
                "capability": "network",
                "allowed": True,
                "reason": "policy_allowed",
            }
        ],
        "capabilities_enabled": [
            {
                "name": "http_client",
                "version": "1.0.0",
                "provided_actions": ["http.get", "http.post"],
                "required_permissions": ["http"],
                "runtime_bindings": {"executor": "namel3ss.runtime.capabilities.http_client"},
                "effect_capabilities": ["network"],
                "contract_version": "runtime-ui@1",
                "purity": "effectful",
                "replay_mode": "verify",
            }
        ],
        "capability_versions": {"http_client": "1.0.0"},
    }


def test_run_artifact_records_capability_usage_deterministically(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    source = app_path.read_text(encoding="utf-8")
    response = _response_with_capability_trace()

    first = build_run_artifact(
        response=response,
        app_path=app_path,
        source=source,
        flow_name="demo",
        action_id=None,
        input_payload={"q": "hello"},
        state_snapshot={},
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
        secret_values=[],
    )
    second = build_run_artifact(
        response=response,
        app_path=app_path,
        source=source,
        flow_name="demo",
        action_id=None,
        input_payload={"q": "hello"},
        state_snapshot={},
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
        secret_values=[],
    )
    assert first == second
    usage = first.get("capability_usage")
    assert isinstance(usage, list) and usage
    assert usage[0]["pack_name"] == "http_client"
    checksums = first.get("checksums") if isinstance(first.get("checksums"), dict) else {}
    assert isinstance(checksums.get("capability_usage_hash"), str)
    assert checksums.get("capability_usage_hash")


def test_replay_detects_capability_usage_mismatch(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    source = app_path.read_text(encoding="utf-8")
    artifact = build_run_artifact(
        response=_response_with_capability_trace(),
        app_path=app_path,
        source=source,
        flow_name="demo",
        action_id=None,
        input_payload={"q": "hello"},
        state_snapshot={},
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
        secret_values=[],
    )
    tampered = deepcopy(artifact)
    usage = tampered.get("capability_usage")
    if isinstance(usage, list) and usage:
        usage[0]["status"] = "blocked"
    replay = replay_run_artifact(tampered)
    assert replay["ok"] is False
    mismatches = replay.get("mismatches")
    assert isinstance(mismatches, list) and mismatches
    assert any(item.get("field") == "checksums.capability_usage_hash" for item in mismatches)
