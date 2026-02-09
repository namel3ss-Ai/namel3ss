from __future__ import annotations

from namel3ss.runtime.trust.trust_score import build_trust_score_details


def test_trust_score_is_high_for_diverse_high_scoring_sources() -> None:
    trace = [
        {
            "chunk_id": "doc-a:0",
            "document_id": "doc-a",
            "score": 0.9,
            "rank": 1,
            "reason": "keyword_match",
            "upload_id": "doc-a",
            "quality": "pass",
        },
        {
            "chunk_id": "doc-b:0",
            "document_id": "doc-b",
            "score": 0.8,
            "rank": 2,
            "reason": "keyword_match",
            "upload_id": "doc-b",
            "quality": "pass",
        },
    ]
    details = build_trust_score_details(retrieval_trace=trace, ingestion_status={"doc-a": {"status": "pass"}})
    assert details["formula_version"] == "rag_trust@1"
    assert details["score"] == 0.8675
    assert details["level"] == "high"


def test_trust_score_penalizes_warn_and_ocr_fallback() -> None:
    trace = [
        {
            "chunk_id": "doc-a:0",
            "document_id": "doc-a",
            "score": 0.2,
            "rank": 1,
            "reason": "fallback_inclusion",
            "upload_id": "doc-a",
            "quality": "warn",
        },
        {
            "chunk_id": "doc-a:1",
            "document_id": "doc-a",
            "score": 0.1,
            "rank": 2,
            "reason": "deterministic_rank",
            "upload_id": "doc-a",
            "quality": "pass",
        },
    ]
    details = build_trust_score_details(retrieval_trace=trace, ingestion_status={"doc-a": {"status": "warn"}})
    assert details["score"] == 0.1025
    assert details["level"] == "low"
    assert details["inputs"]["warn_count"] == 1
    assert details["inputs"]["fallback_count"] == 1


def test_trust_score_for_empty_trace_is_zero() -> None:
    details = build_trust_score_details(retrieval_trace=[], ingestion_status={})
    assert details["score"] == 0.0
    assert details["level"] == "low"
