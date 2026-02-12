from __future__ import annotations

from namel3ss.studio.review.explain_panel import build_explain_panel_payload


def test_explain_panel_builds_envelope_when_missing() -> None:
    payload = build_explain_panel_payload(
        {
            "steps": [{"name": "retrieve"}, {"name": "answer"}],
            "sources_used": [{"source_id": "doc-a:1:0"}],
            "retrieval_stats": {"candidates_considered": 3, "candidates_selected": 1},
            "rationale": "Top citation selected.",
        }
    )
    envelope = payload["trace_envelope"]
    assert payload["error_code"] == "N3E_TRACE_ENVELOPE_MISSING"
    assert envelope["trace_schema_version"] == "trace_envelope@1"
    assert envelope["run_id"].startswith("run_")
    assert envelope["step_ids"]


def test_explain_panel_uses_existing_envelope() -> None:
    trace_envelope = {
        "hashes": {"sources_hash": "a", "steps_hash": "b", "trace_hash": "c"},
        "rationale": "Existing rationale",
        "retrieval_stats": {"candidates_considered": 2, "candidates_selected": 1},
        "run_id": "run-explicit",
        "sources_used": [{"source_id": "doc-a:1:0", "title": "Doc A", "page_number": 1}],
        "step_ids": ["step-1"],
        "trace_schema_version": "trace_envelope@1",
    }
    payload = build_explain_panel_payload({"trace_envelope": trace_envelope})
    assert "error_code" not in payload
    assert payload["trace_envelope"] == trace_envelope
