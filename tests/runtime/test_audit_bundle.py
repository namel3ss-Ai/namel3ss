from __future__ import annotations

from types import SimpleNamespace

from namel3ss.config.model import AppConfig
from namel3ss.runtime.audit.audit_bundle import (
    list_audit_bundles,
    load_run_artifact,
    write_audit_bundle,
)
from namel3ss.runtime.audit.run_artifact import build_run_artifact
from namel3ss.runtime.audit.runtime_capture import attach_audit_artifacts


def _artifact(tmp_path) -> dict[str, object]:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return build_run_artifact(
        response={"ok": True, "state": {}, "result": {"value": "ok"}},
        app_path=app_path,
        source=app_path.read_text(encoding="utf-8"),
        flow_name="demo",
        action_id=None,
        input_payload={},
        state_snapshot={},
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
    )


def test_audit_bundle_write_and_list_are_deterministic(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    first = write_audit_bundle(tmp_path, artifact)
    second = write_audit_bundle(tmp_path, artifact)
    assert first == second
    bundles = list_audit_bundles(tmp_path)
    assert bundles == [first]
    loaded = load_run_artifact(tmp_path, run_id=str(artifact["run_id"]))
    assert loaded == artifact


def test_audit_bundle_is_immutable_per_run_id(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    write_audit_bundle(tmp_path, artifact)
    modified = dict(artifact)
    modified["output"] = {"value": "changed"}
    modified["run_id"] = artifact["run_id"]
    try:
        write_audit_bundle(tmp_path, modified)
    except ValueError as exc:
        assert "Immutable audit file already exists" in str(exc)
    else:  # pragma: no cover - safety net
        raise AssertionError("Expected immutable write failure for modified payload.")


def test_audit_policy_required_and_forbidden_paths(tmp_path) -> None:
    base_response = {"ok": True, "state": {}, "result": {"value": "ok"}}
    required = AppConfig()
    required.audit.mode = "required"
    forbidden = AppConfig()
    forbidden.audit.mode = "forbidden"
    missing_root_program = SimpleNamespace(project_root=None, app_path=None)
    blocked = attach_audit_artifacts(
        dict(base_response),
        program_ir=missing_root_program,
        config=required,
        flow_name="demo",
        input_payload={},
        state_snapshot={},
        source='spec is "1.0"',
        endpoint="/api/action",
    )
    assert blocked["ok"] is False
    assert blocked.get("runtime_error", {}).get("stable_code") == "runtime.policy_denied.audit_required"
    denied = attach_audit_artifacts(
        dict(base_response),
        program_ir=SimpleNamespace(project_root=str(tmp_path), app_path=None),
        config=forbidden,
        flow_name="demo",
        input_payload={},
        state_snapshot={},
        source='spec is "1.0"',
        endpoint="/api/action",
    )
    assert denied.get("run_artifact") is None
    status = denied.get("audit_policy_status")
    assert isinstance(status, dict)
    assert status.get("mode") == "forbidden"
    assert status.get("written") is False
