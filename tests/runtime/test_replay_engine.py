from __future__ import annotations

import json

from namel3ss.runtime.audit.replay_engine import replay_run_artifact, replay_run_artifact_file
from namel3ss.runtime.audit.run_artifact import build_run_artifact


def _artifact(tmp_path) -> dict[str, object]:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return build_run_artifact(
        response={
            "ok": True,
            "state": {},
            "result": {
                "prompt": "question:\ninvoice\n\nanswer:",
                "retrieval": {
                    "retrieval_trace": [
                        {
                            "chunk_id": "doc-1:0",
                            "document_id": "doc-1",
                            "page_number": 1,
                            "score": 0.9,
                            "rank": 1,
                            "reason": "semantic_match",
                        }
                    ]
                },
            },
        },
        app_path=app_path,
        source=app_path.read_text(encoding="utf-8"),
        flow_name="demo",
        action_id=None,
        input_payload={"query": "invoice"},
        state_snapshot={},
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
    )


def test_replay_engine_matches_stable_artifact(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    replay = replay_run_artifact(artifact)
    assert replay["ok"] is True
    assert replay["mismatches"] == []
    assert replay["run_id"] == artifact["run_id"]


def test_replay_engine_reports_mismatch(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    tampered = dict(artifact)
    checksums = dict(tampered.get("checksums") or {})
    checksums["output_hash"] = "deadbeef"
    tampered["checksums"] = checksums
    replay = replay_run_artifact(tampered)
    assert replay["ok"] is False
    mismatches = replay["mismatches"]
    assert isinstance(mismatches, list) and mismatches
    assert any(entry.get("field") == "checksums.output_hash" for entry in mismatches if isinstance(entry, dict))


def test_replay_engine_reads_artifact_file(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    path = tmp_path / "run_artifact.json"
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    replay = replay_run_artifact_file(path)
    assert replay["ok"] is True
    assert replay["artifact_path"] == path.resolve().as_posix()
