from __future__ import annotations

from pathlib import Path

from namel3ss.studio.server import build_session_state
from namel3ss.studio.session import session_storage_path
from namel3ss.studio.workspace import workspace_storage_path


SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def test_workspace_and_session_ids_are_deterministic(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    first = build_session_state(app_path)
    second = build_session_state(app_path)

    assert first.workspace is not None
    assert first.studio_session is not None
    assert second.workspace is not None
    assert second.studio_session is not None
    assert first.workspace.workspace_id == second.workspace.workspace_id
    assert first.studio_session.session_id == second.studio_session.session_id


def test_workspace_and_session_models_persist(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    first = build_session_state(app_path)
    assert first.workspace is not None
    assert first.studio_session is not None
    first.record_run_artifact(
        {
            "run_id": "run-alpha",
            "program": {"app_hash": "app-hash"},
            "inputs": {"payload": {}, "state": {}},
            "prompt": {"text": "", "hash": ""},
            "retrieval_trace": [],
            "trust_score_details": {},
            "runtime_errors": [],
            "output": {"ok": True},
        }
    )

    workspace_id = first.workspace.workspace_id
    workspace_file = workspace_storage_path(tmp_path, workspace_id)
    session_file = session_storage_path(tmp_path, workspace_id)
    assert workspace_file.exists()
    assert session_file.exists()

    second = build_session_state(app_path)
    assert second.studio_session is not None
    assert second.run_history() == ["run-alpha"]
