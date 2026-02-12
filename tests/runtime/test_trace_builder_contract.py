from __future__ import annotations

from namel3ss.runtime.trace.trace_builder import build_trace_envelope


def test_trace_builder_is_deterministic() -> None:
    payload = {"action": "answer", "query": "What changed?"}
    first = build_trace_envelope(
        run_id=None,
        steps=[{"name": "retrieve"}, {"name": "answer"}],
        sources_used=[{"source_id": "doc-b:2:0"}, {"source_id": "doc-a:1:0"}],
        retrieval_stats={"candidates_considered": 5, "candidates_selected": 2},
        rationale="Used highest scoring chunks.",
        payload=payload,
    )
    second = build_trace_envelope(
        run_id=None,
        steps=[{"name": "retrieve"}, {"name": "answer"}],
        sources_used=[{"source_id": "doc-b:2:0"}, {"source_id": "doc-a:1:0"}],
        retrieval_stats={"candidates_considered": 5, "candidates_selected": 2},
        rationale="Used highest scoring chunks.",
        payload=payload,
    )
    assert first == second
    assert first["trace_schema_version"] == "trace_envelope@1"
    assert first["run_id"].startswith("run_")
    assert len(first["step_ids"]) == 2


def test_trace_builder_respects_explicit_run_id() -> None:
    envelope = build_trace_envelope(
        run_id="run-fixed",
        steps=[{"id": "step-1"}],
        sources_used=[],
        retrieval_stats=None,
        rationale=None,
        payload={},
    )
    assert envelope["run_id"] == "run-fixed"
    assert envelope["rationale"] == "No rationale provided."
