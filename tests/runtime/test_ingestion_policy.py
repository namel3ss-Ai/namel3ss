from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.traces.schema import TraceEventType
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _write_policy(root: Path) -> None:
    policy = """[ingestion]
run = true
review = ["ingestion.review"]
override = ["ingestion.override"]
skip = ["ingestion.skip"]

[retrieval]
include_warn = ["retrieval.include_warn"]

[upload]
replace = ["upload.replace"]
"""
    (root / "ingestion.policy.toml").write_text(policy, encoding="utf-8")


def _action_id(program, action_type: str) -> str:
    manifest = build_manifest(program, state={}, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == action_type:
            return action_id
    raise AssertionError(f"Action '{action_type}' not found in manifest")


def _trace_events(payload: dict, event_type: str) -> list[dict]:
    traces = payload.get("traces") if isinstance(payload, dict) else None
    if not isinstance(traces, list):
        return []
    return [trace for trace in traces if isinstance(trace, dict) and trace.get("type") == event_type]


def test_policy_denies_ingestion_review_without_permission(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    _write_policy(tmp_path)
    program = lower_ir_program(source)
    program.app_path = app_path.as_posix()
    program.project_root = str(tmp_path)
    review_action = _action_id(program, "ingestion_review")
    response = handle_action(
        program,
        action_id=review_action,
        payload={},
        state={},
        store=MemoryStore(),
        identity={},
    )
    assert response.get("ok") is False
    assert response.get("kind") == "policy"
    traces = _trace_events(response, TraceEventType.AUTHORIZATION_CHECK)
    outcomes = {entry.get("subject"): entry.get("outcome") for entry in traces}
    assert outcomes == {"policy:ingestion.review": "denied"}


def test_policy_denies_ingestion_override_without_permission(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    _write_policy(tmp_path)
    program = lower_ir_program(source)
    program.app_path = app_path.as_posix()
    program.project_root = str(tmp_path)
    run_action = _action_id(program, "ingestion_run")
    response = handle_action(
        program,
        action_id=run_action,
        payload={"upload_id": "abc123", "mode": "ocr"},
        state={},
        store=MemoryStore(),
        identity={},
    )
    assert response.get("ok") is False
    assert response.get("kind") == "policy"
    traces = _trace_events(response, TraceEventType.AUTHORIZATION_CHECK)
    subjects = {entry.get("subject") for entry in traces}
    assert "policy:ingestion.run" in subjects
    assert "policy:ingestion.override" in subjects
    outcomes = {entry.get("subject"): entry.get("outcome") for entry in traces}
    assert outcomes.get("policy:ingestion.run") == "allowed"
    assert outcomes.get("policy:ingestion.override") == "denied"


def test_declared_policy_denies_ingestion_review_without_permission(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

policy
  require ingestion.review with ingestion.review

page "home":
  upload receipt
'''.lstrip()
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    program = lower_ir_program(source)
    program.app_path = app_path.as_posix()
    program.project_root = str(tmp_path)
    review_action = _action_id(program, "ingestion_review")
    response = handle_action(
        program,
        action_id=review_action,
        payload={},
        state={},
        store=MemoryStore(),
        identity={},
    )
    assert response.get("ok") is False
    assert response.get("kind") == "policy"


def test_policy_defaults_apply_without_block(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

capabilities:
  uploads

page "home":
  upload receipt
'''.lstrip()
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    program = lower_ir_program(source)
    program.app_path = app_path.as_posix()
    program.project_root = str(tmp_path)
    review_action = _action_id(program, "ingestion_review")
    response = handle_action(
        program,
        action_id=review_action,
        payload={},
        state={},
        store=MemoryStore(),
        identity={},
    )
    assert response.get("ok") is True
