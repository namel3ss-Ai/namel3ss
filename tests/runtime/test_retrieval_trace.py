from __future__ import annotations

from namel3ss.runtime.retrieval.retrieval_trace import build_retrieval_trace


def test_retrieval_trace_reasons_and_shape_are_deterministic() -> None:
    results = [
        {
            "chunk_id": "doc-a:0",
            "upload_id": "doc-a",
            "document_id": "doc-a",
            "page_number": 1,
            "ingestion_phase": "deep",
            "quality": "pass",
            "keyword_overlap": 2,
            "vector_score": 0.0,
        },
        {
            "chunk_id": "doc-b:0",
            "upload_id": "doc-b",
            "document_id": "doc-b",
            "page_number": 2,
            "ingestion_phase": "quick",
            "quality": "warn",
            "keyword_overlap": 1,
            "vector_score": 0.0,
        },
        {
            "chunk_id": "doc-c:0",
            "upload_id": "doc-c",
            "document_id": "doc-c",
            "page_number": 3,
            "ingestion_phase": "deep",
            "quality": "pass",
            "keyword_overlap": 0,
            "vector_score": 0.7,
        },
    ]
    ingestion = {
        "doc-a": {"status": "pass", "fallback_used": "ocr"},
        "doc-b": {"status": "warn"},
        "doc-c": {"status": "pass"},
    }

    first = build_retrieval_trace(results, ingestion_status=ingestion)
    second = build_retrieval_trace(results, ingestion_status=ingestion)
    assert first == second

    assert [entry["reason"] for entry in first] == [
        "fallback_inclusion",
        "low_quality_inclusion",
        "semantic_match",
    ]
    assert [entry["rank"] for entry in first] == [1, 2, 3]
    assert all(0.0 <= float(entry["score"]) <= 1.0 for entry in first)
    assert {entry["chunk_id"] for entry in first} == {"doc-a:0", "doc-b:0", "doc-c:0"}


def test_retrieval_trace_defaults_to_deterministic_rank_without_signal() -> None:
    results = [
        {
            "chunk_id": "doc-a:0",
            "upload_id": "doc-a",
            "document_id": "doc-a",
            "page_number": 1,
            "ingestion_phase": "quick",
            "quality": "pass",
            "keyword_overlap": 0,
            "vector_score": 0.0,
        }
    ]
    trace = build_retrieval_trace(results, ingestion_status={})
    assert trace[0]["reason"] == "deterministic_rank"
