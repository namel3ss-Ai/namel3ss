from __future__ import annotations

from pathlib import Path

from namel3ss.rag.ingestion import run_ingestion_pipeline
from namel3ss.rag.observability.explain_service import build_retrieval_explain_payload
from namel3ss.rag.observability.trace_logger import (
    STREAM_EVENT_CITATION_ADD,
    STREAM_EVENT_FINAL,
    STREAM_EVENT_TOKEN,
    STREAM_EVENT_TRACE,
    build_observability_trace_model,
    normalize_stream_events,
)
from namel3ss.rag.retrieval import run_retrieval_service
from namel3ss.rag.retrieval.rerank_service import build_ranked_retrieval_results


def test_phase4_rerank_rows_are_deterministic_with_tie_breaks() -> None:
    results = [
        {"chunk_id": "doc-b:1", "document_id": "doc-b", "page_number": 2},
        {"chunk_id": "doc-a:0", "document_id": "doc-a", "page_number": 1},
    ]
    trace = [
        {
            "chunk_id": "doc-b:1",
            "score": 0.91,
            "score_components": {"raw_score": 0.60},
            "reason": "hybrid_match",
        },
        {
            "chunk_id": "doc-a:0",
            "score": 0.91,
            "score_components": {"raw_score": 0.60},
            "reason": "hybrid_match",
        },
    ]

    first = build_ranked_retrieval_results(results=results, retrieval_trace=trace)
    second = build_ranked_retrieval_results(results=results, retrieval_trace=trace)

    assert first == second
    assert [entry["chunk_id"] for entry in first] == ["doc-a:0", "doc-b:1"]
    assert [entry["rank"] for entry in first] == [1, 2]


def test_phase4_explain_payload_is_deterministic() -> None:
    payload = {
        "query": "policy",
        "retrieval_results": [
            {
                "chunk_id": "doc-b:1",
                "doc_id": "doc-b",
                "page_number": 2,
                "rank": 2,
                "score": 0.8,
                "reason_codes": ["semantic"],
            },
            {
                "chunk_id": "doc-a:0",
                "doc_id": "doc-a",
                "page_number": 1,
                "rank": 1,
                "score": 0.9,
                "reason_codes": ["keyword"],
            },
        ],
        "retrieval_trace": [],
        "retrieval_plan": {"tier": {"selected": "auto", "requested": "auto"}},
        "retrieval_tuning": {"semantic_weight": 0.5, "semantic_k": 10, "lexical_k": 10, "final_top_k": 8},
        "trust_score_details": {"level": "high", "score": 0.9},
        "retrieval_scope": {
            "active": True,
            "requested": {"collections": ["kb.z", "kb.a"], "documents": ["doc.z", "doc.a"]},
            "resolved_documents": ["doc.a", "doc.z"],
        },
    }

    first = build_retrieval_explain_payload(**payload)
    second = build_retrieval_explain_payload(**payload)

    assert first == second
    assert first["retrieval_scope"] == {
        "active": True,
        "requested": {
            "collections": ["kb.a", "kb.z"],
            "documents": ["doc.a", "doc.z"],
        },
        "resolved_documents": ["doc.a", "doc.z"],
    }
    assert [entry["chunk_id"] for entry in first["retrieval_trace"]] == ["doc-a:0", "doc-b:1"]


def test_phase4_stream_event_sequence_contract_is_strict() -> None:
    events = normalize_stream_events(
        [
            {"event_type": STREAM_EVENT_FINAL, "payload": {"done": True}, "sequence": 1},
            {"event_type": STREAM_EVENT_TOKEN, "payload": {"token": "alpha"}, "sequence": 1},
            {"event_type": STREAM_EVENT_CITATION_ADD, "payload": {"citation_id": "cit.b"}, "sequence": 1},
            {"event_type": STREAM_EVENT_TRACE, "payload": {"step": "retrieval"}, "sequence": 1},
            {"event_type": "ignored", "payload": {}, "sequence": 1},
        ]
    )

    assert [entry["event_type"] for entry in events] == [
        STREAM_EVENT_TOKEN,
        STREAM_EVENT_CITATION_ADD,
        STREAM_EVENT_TRACE,
        STREAM_EVENT_FINAL,
    ]
    assert [entry["sequence"] for entry in events] == [1, 2, 3, 4]


def test_phase4_retrieval_service_emits_observability_contracts_end_to_end() -> None:
    state: dict = {}
    run_ingestion_pipeline(
        state=state,
        content=b"Alpha policy runbook and escalation.",
        source_name="alpha.txt",
        source_identity="fixtures/phase4-alpha.txt",
        source_type="upload",
        source_uri="upload://fixtures/phase4-alpha.txt",
        mime_type="text/plain",
    )
    run_ingestion_pipeline(
        state=state,
        content=b"Beta policy runbook and support.",
        source_name="beta.txt",
        source_identity="fixtures/phase4-beta.txt",
        source_type="upload",
        source_uri="upload://fixtures/phase4-beta.txt",
        mime_type="text/plain",
    )

    first = run_retrieval_service(
        query="policy",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config={"top_k": 5, "filters": {"tags": []}, "scope": {"collections": [], "documents": []}},
    )
    second = run_retrieval_service(
        query="policy",
        state=state,
        project_root=None,
        app_path=None,
        retrieval_config={"top_k": 5, "filters": {"tags": []}, "scope": {"collections": [], "documents": []}},
    )

    assert first == second
    assert first["retrieval_explain"]["schema_version"] == "rag.explain@1"
    assert first["observability_trace"]["schema_version"] == "rag.trace@1"
    event_types = [entry.get("event_type") for entry in first["observability_trace"]["events"]]
    assert event_types[-1] == STREAM_EVENT_FINAL
    assert set(event_types).issubset({STREAM_EVENT_TOKEN, STREAM_EVENT_CITATION_ADD, STREAM_EVENT_TRACE, STREAM_EVENT_FINAL})


__all__ = []
