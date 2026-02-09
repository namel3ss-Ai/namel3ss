from __future__ import annotations

from pathlib import Path

from namel3ss.studio.server import build_session_state
from namel3ss.studio.share.repro_bundle import (
    build_repro_bundle,
    load_repro_bundle,
    write_repro_bundle,
)


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


def test_repro_bundle_round_trip_is_deterministic(tmp_path: Path) -> None:
    artifact = {
        "run_id": "run-123",
        "program": {"app_hash": "app-hash", "entrypoint": "flow:demo"},
        "inputs": {"payload": {"q": "hello"}, "state": {"x": 1}},
        "prompt": {"text": "prompt", "hash": "hash"},
        "output": {"answer": "ok"},
        "retrieval_trace": [{"chunk_id": "c1", "document_id": "doc-1", "page_number": 1, "score": 0.7, "rank": 1, "reason": "semantic"}],
        "trust_score_details": {"score": 0.8, "level": "medium"},
        "runtime_errors": [],
    }
    first = build_repro_bundle(run_artifact=artifact, workspace_id="workspace_1", session_id="session_1")
    second = build_repro_bundle(run_artifact=artifact, workspace_id="workspace_1", session_id="session_1")
    assert first == second

    path = write_repro_bundle(tmp_path, first)
    assert path.exists()
    loaded = load_repro_bundle(tmp_path, run_id="run-123")
    assert loaded == first
    assert load_repro_bundle(tmp_path) == first


def test_session_records_repro_bundle_for_latest_run(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    session = build_session_state(app_path)
    session.record_run_artifact(
        {
            "run_id": "run-latest",
            "program": {"app_hash": "app-hash", "entrypoint": "flow:demo"},
            "inputs": {"payload": {}, "state": {}},
            "prompt": {"text": "", "hash": ""},
            "output": {"answer": "ok"},
            "retrieval_trace": [],
            "trust_score_details": {},
            "runtime_errors": [],
        }
    )
    bundle = load_repro_bundle(tmp_path)
    assert bundle is not None
    assert bundle["run_id"] == "run-latest"
