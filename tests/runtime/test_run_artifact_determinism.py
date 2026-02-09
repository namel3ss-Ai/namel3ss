from __future__ import annotations

import json

from namel3ss.runtime.audit.run_artifact import build_run_artifact


def _sample_response() -> dict:
    return {
        "ok": True,
        "state": {
            "ingestion": {"upload-1": {"status": "warn", "fallback_used": "ocr"}},
            "retrieval": {
                "retrieval_plan": {"query": "invoice"},
                "retrieval_trace": [
                    {
                        "chunk_id": "doc-1:0",
                        "document_id": "doc-1",
                        "page_number": 1,
                        "score": 0.91,
                        "rank": 1,
                        "reason": "semantic_match",
                    }
                ],
                "trust_score_details": {"formula_version": "rag_trust@1", "score": 0.82, "level": "high"},
            },
        },
        "result": {
            "retrieval": {
                "query": "invoice",
                "retrieval_plan": {"query": "invoice"},
                "retrieval_trace": [
                    {
                        "chunk_id": "doc-1:0",
                        "document_id": "doc-1",
                        "page_number": 1,
                        "score": 0.91,
                        "rank": 1,
                        "reason": "semantic_match",
                    }
                ],
                "trust_score_details": {"formula_version": "rag_trust@1", "score": 0.82, "level": "high"},
            }
        },
    }


def test_run_artifact_is_deterministic_and_scrubbed(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    source = app_path.read_text(encoding="utf-8")
    response = _sample_response()
    first = build_run_artifact(
        response=response,
        app_path=app_path,
        source=source,
        flow_name="demo",
        action_id=None,
        input_payload={"query": "invoice"},
        state_snapshot=response["state"],
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
        input_payload={"query": "invoice"},
        state_snapshot=response["state"],
        provider_name="mock",
        model_name="mock-model",
        project_root=tmp_path,
        secret_values=[],
    )
    assert first == second
    assert first["schema_version"] == "run_artifact@1"
    assert isinstance(first.get("run_id"), str) and len(str(first.get("run_id"))) == 64
    text = json.dumps(first, sort_keys=True)
    for key in ("timestamp", "time_start", "time_end", "trace_id", "duration_ms", "call_id"):
        assert key not in text
